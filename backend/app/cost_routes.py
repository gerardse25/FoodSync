from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import app.auth
import app.cost_schemas as schemas
from app.database import get_db
from app.home_models import HomeMembership
from app.inventory_models import CostSettlement, InventoryProduct, InventoryProductOwner
from app.inventory_routes import (
    _get_active_home,
    _get_active_membership,
    _json_error,
)

router = APIRouter(prefix="/inventory/costs", tags=["inventory", "costs"])

Period = Literal["weekly", "monthly", "yearly"]

def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _money_str(value: Decimal) -> str:
    return str(_money(value))


def _default_date_range(period: Period) -> tuple[date, date]:
    today = date.today()

    if period == "weekly":
        return today - timedelta(weeks=12), today

    if period == "monthly":
        return today - timedelta(days=365), today

    return date(today.year - 4, 1, 1), today


def _period_key_and_range(value: date, period: Period) -> tuple[str, date, date]:
    if period == "weekly":
        start = value - timedelta(days=value.weekday())
        end = start + timedelta(days=6)
        iso_year, iso_week, _ = value.isocalendar()
        return f"{iso_year}-W{iso_week:02d}", start, end

    if period == "monthly":
        start = date(value.year, value.month, 1)

        if value.month == 12:
            end = date(value.year, 12, 31)
        else:
            end = date(value.year, value.month + 1, 1) - timedelta(days=1)

        return f"{value.year}-{value.month:02d}", start, end

    start = date(value.year, 1, 1)
    end = date(value.year, 12, 31)
    return str(value.year), start, end


def _line_cost(product: InventoryProduct) -> Decimal:
    """
    Retorna el cost econòmic del producte.

    En FoodSync, el camp preu representa el total de la línia/producte
    introduït manualment, per codi de barres o extret del tiquet.
    """
    if product.preu is None:
        return Decimal("0.00")

    return Decimal(str(product.preu))


def _get_active_home_or_error(user_id, db: Session):
    membership = _get_active_membership(user_id, db)
    if not membership:
        return None, _json_error("No pertanys a cap llar.", 404, "NOT_IN_HOME")

    home = _get_active_home(membership.home_id, db)
    if not home:
        return None, _json_error("La llar no existeix o no és activa.", 404, "HOME_NOT_FOUND")

    return home, None


def _get_products_for_costs(
    home_id,
    db: Session,
    date_from: Optional[date],
    date_to: date,
):
    query = (
        db.query(InventoryProduct)
        .filter(InventoryProduct.id_llar == home_id)
        .filter(InventoryProduct.preu.isnot(None))
        .filter(InventoryProduct.data_compra.isnot(None))
        .filter(InventoryProduct.data_compra <= date_to)
    )

    if date_from is not None:
        query = query.filter(InventoryProduct.data_compra >= date_from)

    return query.all()


def _get_active_member_ids(home_id, db: Session) -> list:
    memberships = (
        db.query(HomeMembership)
        .filter(HomeMembership.home_id == home_id)
        .all()
    )

    member_ids = []
    for membership in memberships:
        if getattr(membership, "is_active", True) is False:
            continue
        if getattr(membership, "left_at", None) is not None:
            continue
        member_ids.append(membership.user_id)

    return member_ids


def _get_owner_map(product_ids: list[int], db: Session) -> dict[int, list]:
    if not product_ids:
        return {}

    owners = (
        db.query(InventoryProductOwner)
        .filter(InventoryProductOwner.id_inventari.in_(product_ids))
        .all()
    )

    result: dict[int, list] = defaultdict(list)
    for owner in owners:
        result[owner.id_inventari].append(owner.user_id)

    return result

def _parse_money(value: str) -> Decimal:
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        raise ValueError("INVALID_AMOUNT")

    if amount <= 0:
        raise ValueError("INVALID_AMOUNT")

    if amount.as_tuple().exponent < -2:
        raise ValueError("INVALID_AMOUNT")

    return _money(amount)


def _get_settlements_for_period(
    home_id,
    db: Session,
    date_from: Optional[date],
    date_to: date,
):
    query = (
        db.query(CostSettlement)
        .filter(CostSettlement.home_id == home_id)
    )

    if date_from is None:
        query = query.filter(CostSettlement.date_from.is_(None))
        query = query.filter(CostSettlement.date_to.is_(None))
    else:
        query = query.filter(CostSettlement.date_from == date_from)
        query = query.filter(CostSettlement.date_to == date_to)

    return query.all()


def _apply_settlements_to_balances(
    balances: dict,
    settlements: list[CostSettlement],
) -> tuple[dict, dict]:
    settled_paid = {member_id: Decimal("0.00") for member_id in balances}
    settled_received = {member_id: Decimal("0.00") for member_id in balances}

    for settlement in settlements:
        from_user_id = settlement.from_user_id
        to_user_id = settlement.to_user_id
        amount = Decimal(str(settlement.amount))

        if from_user_id not in balances or to_user_id not in balances:
            continue

        # Si A paga a B:
        # - A redueix el seu deute: balance puja.
        # - B redueix el que havia de cobrar: balance baixa.
        balances[from_user_id] += amount
        balances[to_user_id] -= amount

        settled_paid[from_user_id] += amount
        settled_received[to_user_id] += amount

    return settled_paid, settled_received


def _build_minimized_transfers(
    balances: dict,
) -> list[schemas.CostTransfer]:
    debtors = [
        [member_id, -balance]
        for member_id, balance in balances.items()
        if balance < 0
    ]
    creditors = [
        [member_id, balance]
        for member_id, balance in balances.items()
        if balance > 0
    ]

    transfers: list[schemas.CostTransfer] = []

    i = 0
    j = 0

    while i < len(debtors) and j < len(creditors):
        debtor_id, debt_amount = debtors[i]
        creditor_id, credit_amount = creditors[j]

        amount = _money(min(debt_amount, credit_amount))

        if amount > 0:
            transfers.append(
                schemas.CostTransfer(
                    from_user_id=str(debtor_id),
                    to_user_id=str(creditor_id),
                    amount=_money_str(amount),
                )
            )

        debtors[i][1] -= amount
        creditors[j][1] -= amount

        if debtors[i][1] <= Decimal("0.00"):
            i += 1

        if creditors[j][1] <= Decimal("0.00"):
            j += 1

    return transfers


def _calculate_cost_split(
    home_id,
    db: Session,
    date_from: Optional[date],
    date_to: date,
) -> schemas.CostSplitResponse:
    member_ids = _get_active_member_ids(home_id, db)

    products = _get_products_for_costs(
        home_id=home_id,
        db=db,
        date_from=date_from,
        date_to=date_to,
    )

    owner_map = _get_owner_map(
        [product.id_inventari for product in products],
        db,
    )

    should_pay: dict = {member_id: Decimal("0.00") for member_id in member_ids}
    paid: dict = {member_id: Decimal("0.00") for member_id in member_ids}

    total = Decimal("0.00")

    for product in products:
        cost = _line_cost(product)
        if cost <= 0:
            continue

        payer_id = product.paid_by_user_id

        if payer_id is None:
            # En una BD nova no hauria de passar.
            # Ignorem productes sense pagador per no inventar qui ha pagat.
            continue

        if payer_id not in member_ids:
            continue

        owners = owner_map.get(product.id_inventari, [])

        if product.es_privat and owners:
            participants = [owner for owner in owners if owner in member_ids]
            if not participants:
                continue
        else:
            participants = member_ids

        share = cost / Decimal(len(participants))

        for participant in participants:
            should_pay[participant] += share

        paid[payer_id] += cost
        total += cost

    balances = {
        member_id: _money(paid[member_id] - should_pay[member_id])
        for member_id in member_ids
    }

    settlements = _get_settlements_for_period(
        home_id=home_id,
        db=db,
        date_from=date_from,
        date_to=date_to,
    )

    settled_paid, settled_received = _apply_settlements_to_balances(
        balances,
        settlements,
    )

    balances = {
        member_id: _money(balance)
        for member_id, balance in balances.items()
    }

    transfers = _build_minimized_transfers(balances)

    members = [
        schemas.CostMemberShare(
            user_id=str(member_id),
            should_pay=_money_str(should_pay[member_id]),
            paid=_money_str(paid[member_id]),
            settled_paid=_money_str(settled_paid[member_id]),
            settled_received=_money_str(settled_received[member_id]),
            balance=_money_str(balances[member_id]),
        )
        for member_id in member_ids
    ]

    return schemas.CostSplitResponse(
        date_from=date_from,
        date_to=date_to,
        total=_money_str(total),
        members=members,
        transfers=transfers,
    )


@router.get("/summary", response_model=schemas.CostSummaryResponse)
def get_cost_summary(
    period: Period = Query("monthly"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    RF-COST-01.
    Retorna la sèrie temporal de despeses de la llar perquè el frontend
    pugui pintar un únic gràfic de costos.

    Paràmetres:
    - period: agrupació del gràfic. Pot ser "weekly", "monthly" o "yearly".
      Per defecte és "monthly".
    - date_from/date_to: rang opcional de dates de compra. Si no s'informen,
      el backend aplica un rang per defecte segons el període:
        * weekly  -> últimes 12 setmanes
        * monthly -> últim any
        * yearly  -> últims 4 anys

    Regles:
    - Inclou productes manuals, productes per codi de barres i productes de tiquet.
    - Només compta productes amb preu i data_compra.
    - El camp preu s'interpreta com el total de la línia/producte.
    - No distingeix productes privats: el gràfic mostra despesa total de la llar.

    Ús frontend:
    - Mostrar selector Setmanal / Mensual / Anual.
    - Pintar series[].period a l'eix X i series[].total a l'eix Y.
    """
    user, _session = current

    home, error = _get_active_home_or_error(user.id, db)
    if error:
        return error

    default_from, default_to = _default_date_range(period)
    date_from = date_from or default_from
    date_to = date_to or default_to

    if date_from > date_to:
        return _json_error(
            "La data inicial no pot ser posterior a la data final.",
            422,
            "INVALID_DATE_RANGE",
        )

    products = _get_products_for_costs(
        home_id=home.id,
        db=db,
        date_from=date_from,
        date_to=date_to,
    )

    buckets: dict[str, dict] = {}

    total = Decimal("0.00")
    item_count = 0

    for product in products:
        cost = _line_cost(product)
        if cost <= 0:
            continue

        key, start, end = _period_key_and_range(product.data_compra, period)

        if key not in buckets:
            buckets[key] = {
                "period": key,
                "start_date": start,
                "end_date": end,
                "total": Decimal("0.00"),
                "item_count": 0,
            }

        buckets[key]["total"] += cost
        buckets[key]["item_count"] += 1
        total += cost
        item_count += 1

    series = [
        schemas.CostSeriesPoint(
            period=bucket["period"],
            start_date=bucket["start_date"],
            end_date=bucket["end_date"],
            total=_money_str(bucket["total"]),
            item_count=bucket["item_count"],
        )
        for bucket in sorted(buckets.values(), key=lambda x: x["start_date"])
    ]

    return schemas.CostSummaryResponse(
        period=period,
        date_from=date_from,
        date_to=date_to,
        total=_money_str(total),
        item_count=item_count,
        series=series,
    )


@router.get("/split", response_model=schemas.CostSplitResponse)
def get_cost_split(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    RF-COST-02.
    Calcula el balanç econòmic pendent de cada membre de la llar i genera
    les transferències mínimes recomanades, a l'estil Tricount.

    Paràmetres:
    - date_from/date_to: rang opcional de dates de compra.
      Si no s'informa date_from, el repartiment és acumulat històricament
      fins a date_to. Si tampoc s'informa date_to, s'utilitza la data actual.

    Regles de càlcul:
    - Cada producte té un pagador real: InventoryProduct.paid_by_user_id.
    - Si el producte és compartit, el cost es reparteix entre tots els membres
      actius de la llar.
    - Si el producte és privat, el cost només es reparteix entre els seus
      propietaris privats.
    - Només compten productes amb preu, data_compra i paid_by_user_id.
    - Els pagaments marcats amb “Està pagat!” es resten del saldo pendent.
    - El camp preu s'interpreta com el total de la línia/producte.

    Interpretació:
    - paid: diners que ha pagat aquell membre en compres.
    - should_pay: diners que li corresponien segons el repartiment.
    - settled_paid: diners que ja ha pagat a altres membres.
    - settled_received: diners que ja ha rebut d'altres membres.
    - balance positiu: ha de rebre diners.
    - balance negatiu: ha de pagar diners.
    - transfers indica les transferències pendents recomanades.
    """
    user, _session = current

    home, error = _get_active_home_or_error(user.id, db)
    if error:
        return error

    date_to = date_to or date.today()

    if date_from is not None and date_from > date_to:
        return _json_error(
            "La data inicial no pot ser posterior a la data final.",
            422,
            "INVALID_DATE_RANGE",
        )

    member_ids = _get_active_member_ids(home.id, db)
    if not member_ids:
        return _json_error(
            "No hi ha membres actius a la llar.",
            404,
            "NO_ACTIVE_MEMBERS",
        )

    return _calculate_cost_split(
        home_id=home.id,
        db=db,
        date_from=date_from,
        date_to=date_to,
    )

@router.post("/settlements", response_model=schemas.CreateCostSettlementResponse)
def create_cost_settlement(
    data: schemas.CreateCostSettlementRequest,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Marca una transferència recomanada com a pagada.

    Ús frontend:
    - El frontend mostra una transferència pendent de /inventory/costs/split.
    - Quan l'usuari prem “Està pagat!”, envia from_user_id, to_user_id,
      amount i el mateix rang date_from/date_to que estava consultant.
    - El backend valida que aquesta transferència encara estigui pendent.
    - Si és vàlida, guarda una liquidació a cost_settlements.
    - La resposta retorna el nou split ja actualitzat.
    """
    user, _session = current

    home, error = _get_active_home_or_error(user.id, db)
    if error:
        return error

    date_to = data.date_to or date.today()

    if data.date_from is not None and data.date_from > date_to:
        return _json_error(
            "La data inicial no pot ser posterior a la data final.",
            422,
            "INVALID_DATE_RANGE",
        )

    member_ids = _get_active_member_ids(home.id, db)

    if data.from_user_id not in member_ids:
        return _json_error(
            "L'usuari pagador no pertany a la llar.",
            422,
            "PAYER_NOT_IN_HOME",
        )

    if data.to_user_id not in member_ids:
        return _json_error(
            "L'usuari receptor no pertany a la llar.",
            422,
            "RECEIVER_NOT_IN_HOME",
        )

    if data.from_user_id == data.to_user_id:
        return _json_error(
            "El pagador i el receptor no poden ser el mateix usuari.",
            422,
            "SAME_PAYER_AND_RECEIVER",
        )

    try:
        amount = _parse_money(data.amount)
    except ValueError:
        return _json_error(
            "L'import del pagament no és vàlid.",
            422,
            "INVALID_SETTLEMENT_AMOUNT",
        )

    current_split = _calculate_cost_split(
        home_id=home.id,
        db=db,
        date_from=data.date_from,
        date_to=date_to,
    )

    matching_transfer = None
    for transfer in current_split.transfers:
        if (
            transfer.from_user_id == str(data.from_user_id)
            and transfer.to_user_id == str(data.to_user_id)
        ):
            matching_transfer = transfer
            break

    if matching_transfer is None:
        return _json_error(
            "No existeix cap transferència pendent entre aquests usuaris.",
            422,
            "TRANSFER_NOT_PENDING",
        )

    pending_amount = Decimal(matching_transfer.amount)

    if amount > pending_amount:
        return _json_error(
            "L'import supera la transferència pendent.",
            422,
            "SETTLEMENT_AMOUNT_TOO_HIGH",
        )

    settlement = CostSettlement(
        home_id=home.id,
        from_user_id=data.from_user_id,
        to_user_id=data.to_user_id,
        amount=amount,
        date_from=data.date_from,
        date_to=data.date_to if data.date_from is not None else None,
        created_by_user_id=user.id,
    )

    db.add(settlement)
    db.commit()
    db.refresh(settlement)

    updated_split = _calculate_cost_split(
        home_id=home.id,
        db=db,
        date_from=data.date_from,
        date_to=date_to,
    )

    return schemas.CreateCostSettlementResponse(
        missatge="Pagament registrat correctament.",
        settlement=schemas.CostSettlementItem(
            id=settlement.id,
            from_user_id=str(settlement.from_user_id),
            to_user_id=str(settlement.to_user_id),
            amount=_money_str(Decimal(str(settlement.amount))),
            date_from=settlement.date_from,
            date_to=settlement.date_to,
            paid_at=settlement.paid_at,
        ),
        split=updated_split,
    )