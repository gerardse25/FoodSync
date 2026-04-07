import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from jose import JWTError
from sqlalchemy.orm import Session

import app.auth
import app.models
import app.schemas
from app.database import get_db
from app.validation import contains_control_characters, contains_escape_sequences

router = APIRouter(prefix="/auth", tags=["auth"])


def _json_error(code: str, detail: str, status_code: int = 400):
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "code": code,
        },
    )


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_REGEX = re.compile(r"^[A-Za-z0-9_.-]+$")


def _is_valid_email_format(email: str) -> bool:
    if not EMAIL_REGEX.match(email):
        return False

    local_part, _, domain = email.partition("@")

    if not local_part or not domain:
        return False

    if domain.startswith(".") or domain.endswith("."):
        return False

    if "." not in domain:
        return False

    return True


def _normalize_email_for_storage(email: str) -> str:
    email = email.strip()
    local_part, _, domain = email.partition("@")
    return f"{local_part}@{domain.lower()}"


def _validate_password_field(value: str, prefix: str):
    raw_value = value if value is not None else ""
    trimmed_value = raw_value.strip()

    if not trimmed_value:
        return None, _json_error(
            f"{prefix}_REQUIRED",
            "Aquest camp és obligatori",
        )

    if len(trimmed_value) < 6:
        return None, _json_error(
            f"{prefix}_TOO_SHORT",
            "La contrasenya és massa curta",
        )

    if len(trimmed_value) > 32:
        return None, _json_error(
            f"{prefix}_TOO_LONG",
            "La contrasenya és massa llarga",
        )

    if (
        contains_control_characters(trimmed_value)
        or contains_escape_sequences(trimmed_value)
    ):
        return None, _json_error(
            f"{prefix}_INVALID_CHARACTERS",
            "La contrasenya conté caràcters no permesos",
        )

    if any(ch.isspace() for ch in trimmed_value):
        return None, _json_error(
            f"{prefix}_INVALID_SPACES",
            "La contrasenya no pot contenir espais interns",
        )

    return trimmed_value, None


def _validate_change_password_input(current_password: str, new_password: str):
    raw_current = current_password if current_password is not None else ""
    raw_new = new_password if new_password is not None else ""

    trimmed_current = raw_current.strip()
    trimmed_new = raw_new.strip()

    if not trimmed_current and not trimmed_new:
        return None, None, _json_error(
            "REQUIRED_FIELDS_MISSING",
            "Cal informar contrasenya actual i nova contrasenya",
        )

    validated_current, error = _validate_password_field(
        raw_current, "CURRENT_PASSWORD"
    )
    if error:
        return None, None, error

    validated_new, error = _validate_password_field(raw_new, "NEW_PASSWORD")
    if error:
        return None, None, error

    return validated_current, validated_new, None


def _validate_reset_password_input(new_password: str):
    validated_new, error = _validate_password_field(new_password, "NEW_PASSWORD")
    return validated_new, error


def _validate_register_input(email: str, username: str, password: str):
    raw_email = email if email is not None else ""
    raw_username = username if username is not None else ""
    raw_password = password if password is not None else ""

    trimmed_email = raw_email.strip()
    trimmed_username = raw_username.strip()
    trimmed_password = raw_password.strip()

    if not trimmed_email and not trimmed_username and not trimmed_password:
        return None, None, None, None, _json_error(
            "REQUIRED_FIELDS_MISSING",
            "Cal informar correu, nom d'usuari i contrasenya",
        )

    if not trimmed_email:
        return None, None, None, None, _json_error(
            "EMAIL_REQUIRED",
            "El correu és obligatori",
        )

    if not trimmed_username:
        return None, None, None, None, _json_error(
            "USERNAME_REQUIRED",
            "El nom d'usuari és obligatori",
        )

    if not trimmed_password:
        return None, None, None, None, _json_error(
            "PASSWORD_REQUIRED",
            "La contrasenya és obligatòria",
        )

    if len(trimmed_email) > 128:
        return None, None, None, None, _json_error(
            "EMAIL_TOO_LONG",
            "El correu és massa llarg",
        )

    if (
        contains_control_characters(trimmed_email)
        or contains_escape_sequences(trimmed_email)
    ):
        return None, None, None, None, _json_error(
            "EMAIL_INVALID_CHARACTERS",
            "El correu conté caràcters no permesos",
        )

    if any(ch.isspace() for ch in trimmed_email):
        if re.search(r"\s@", trimmed_email) or re.search(r"@\s", trimmed_email):
            return None, None, None, None, _json_error(
                "EMAIL_INVALID_SPACES",
                "El correu no pot contenir espais interns",
            )

        return None, None, None, None, _json_error(
            "EMAIL_INVALID_FORMAT",
            "El format del correu és invàlid",
        )

    if not _is_valid_email_format(trimmed_email):
        return None, None, None, None, _json_error(
            "EMAIL_INVALID_FORMAT",
            "El format del correu és invàlid",
        )

    if len(trimmed_username) < 2:
        return None, None, None, None, _json_error(
            "USERNAME_TOO_SHORT",
            "El nom d'usuari és massa curt",
        )

    if len(trimmed_username) > 16:
        return None, None, None, None, _json_error(
            "USERNAME_TOO_LONG",
            "El nom d'usuari és massa llarg",
        )

    if (
        contains_control_characters(trimmed_username)
        or contains_escape_sequences(trimmed_username)
    ):
        return None, None, None, None, _json_error(
            "USERNAME_INVALID_CHARACTERS",
            "El nom d'usuari conté caràcters no permesos",
        )

    if any(ch.isspace() for ch in trimmed_username):
        return None, None, None, None, _json_error(
            "USERNAME_INVALID_SPACES",
            "El nom d'usuari no pot contenir espais interns",
        )

    if not USERNAME_REGEX.fullmatch(trimmed_username):
        return None, None, None, None, _json_error(
            "USERNAME_INVALID_CHARACTERS",
            "El nom d'usuari conté caràcters no permesos",
        )

    if len(trimmed_password) < 6:
        return None, None, None, None, _json_error(
            "PASSWORD_TOO_SHORT",
            "La contrasenya és massa curta",
        )

    if len(trimmed_password) > 32:
        return None, None, None, None, _json_error(
            "PASSWORD_TOO_LONG",
            "La contrasenya és massa llarga",
        )

    if (
        contains_control_characters(trimmed_password)
        or contains_escape_sequences(trimmed_password)
    ):
        return None, None, None, None, _json_error(
            "PASSWORD_INVALID_CHARACTERS",
            "La contrasenya conté caràcters no permesos",
        )

    if any(ch.isspace() for ch in trimmed_password):
        return None, None, None, None, _json_error(
            "PASSWORD_INVALID_SPACES",
            "La contrasenya no pot contenir espais interns",
        )

    display_email = _normalize_email_for_storage(trimmed_email)
    normalized_email = trimmed_email.lower()

    return display_email, normalized_email, trimmed_username, trimmed_password, None


def _validate_login_input(email: str, password: str):
    raw_email = email if email is not None else ""
    raw_password = password if password is not None else ""

    trimmed_email = raw_email.strip()
    trimmed_password = raw_password.strip()

    if not trimmed_email and not trimmed_password:
        return (
            None,
            None,
            _json_error(
                "REQUIRED_FIELDS_MISSING",
                "Cal informar correu i contrasenya",
            ),
        )

    if not trimmed_email:
        return (
            None,
            None,
            _json_error(
                "EMAIL_REQUIRED",
                "El correu és obligatori",
            ),
        )

    if not trimmed_password:
        return (
            None,
            None,
            _json_error(
                "PASSWORD_REQUIRED",
                "La contrasenya és obligatòria",
            ),
        )

    if len(trimmed_email) > 128:
        return (
            None,
            None,
            _json_error(
                "EMAIL_INVALID_FORMAT",
                "El format del correu és invàlid",
            ),
        )

    if contains_control_characters(trimmed_email) or contains_escape_sequences(
        trimmed_email
    ):
        return (
            None,
            None,
            _json_error(
                "EMAIL_INVALID_CHARACTERS",
                "El correu conté caràcters no permesos",
            ),
        )

    if any(ch.isspace() for ch in trimmed_email):
        return (
            None,
            None,
            _json_error(
                "EMAIL_INVALID_SPACES",
                "El correu no pot contenir espais interns",
            ),
        )

    if not _is_valid_email_format(trimmed_email):
        return (
            None,
            None,
            _json_error(
                "EMAIL_INVALID_FORMAT",
                "El format del correu és invàlid",
            ),
        )

    if contains_control_characters(trimmed_password) or contains_escape_sequences(
        trimmed_password
    ):
        return (
            None,
            None,
            _json_error(
                "PASSWORD_INVALID_CHARACTERS",
                "La contrasenya conté caràcters no permesos",
            ),
        )

    if any(ch.isspace() for ch in trimmed_password):
        return (
            None,
            None,
            _json_error(
                "PASSWORD_INVALID_SPACES",
                "La contrasenya no pot contenir espais interns",
            ),
        )

    normalized_email = trimmed_email.lower()
    return normalized_email, trimmed_password, None


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: app.schemas.RegisterSchema, db: Session = Depends(get_db)):
    (
        display_email,
        normalized_email,
        normalized_username,
        normalized_password,
        validation_response,
    ) = _validate_register_input(data.email, data.username, data.password)

    if validation_response:
        return validation_response

    existing_user = (
        db.query(app.models.User)
        .filter(app.models.User.email_normalized == normalized_email)
        .first()
    )

    if existing_user:
        return JSONResponse(
            status_code=409,
            content={
                "detail": "Aquest correu electrònic ja està registrat",
                "code": "EMAIL_ALREADY_REGISTERED",
            },
        )

    new_user = app.models.User(
        username=normalized_username,
        email=display_email,
        email_normalized=normalized_email,
        password_hash=app.auth.hash_password(normalized_password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    session_id = uuid.uuid4()
    refresh_token, refresh_expire = app.auth.create_refresh_token(
        {"sub": str(new_user.id), "sid": str(session_id)}
    )

    session = app.models.Session(
        id=session_id,
        user_id=new_user.id,
        refresh_token=refresh_token,
        expires_at=refresh_expire,
        is_active=True,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    access_token = app.auth.create_access_token(
        {"sub": str(new_user.id), "sid": str(session.id)}
    )

    return JSONResponse(
        status_code=201,
        content={
            "message": "Compte creat correctament",
            "code": "ACCOUNT_CREATED",
            "user": {
                "id": str(new_user.id),
                "username": new_user.username,
                "email": new_user.email,
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
    )


@router.post("/login")
def login(data: app.schemas.LoginSchema, db: Session = Depends(get_db)):
    normalized_email, trimmed_password, validation_response = _validate_login_input(
        data.email, data.password
    )
    if validation_response:
        return validation_response

    user = (
        db.query(app.models.User)
        .filter(
            app.models.User.email_normalized == normalized_email,
            app.models.User.is_active,
        )
        .first()
    )

    if not user or not app.auth.verify_password(
        trimmed_password,
        user.password_hash,
    ):
        return JSONResponse(
            status_code=401,
            content={
                "detail": "Credencials incorrectes",
                "code": "INVALID_CREDENTIALS",
            },
        )

    session_id = uuid.uuid4()
    refresh_token, refresh_expire = app.auth.create_refresh_token(
        {"sub": str(user.id), "sid": str(session_id)}
    )

    session = app.models.Session(
        id=session_id,
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=refresh_expire,
        is_active=True,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    access_token = app.auth.create_access_token(
        {"sub": str(user.id), "sid": str(session.id)}
    )

    return {
        "message": "Inici de sessió exitós",
        "code": "LOGIN_SUCCESS",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
        },
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@router.post("/refresh")
def refresh_token(data: app.schemas.RefreshSchema, db: Session = Depends(get_db)):
    try:
        payload = app.auth.decode_token(data.refresh_token)
        user_id = payload.get("sub")
        session_id = payload.get("sid")
        token_type = payload.get("type")

        if token_type != "refresh" or not user_id or not session_id:
            raise HTTPException(status_code=401, detail="Token invàlid")

    except JWTError as err:
        raise HTTPException(status_code=401, detail="Token invàlid") from err

    session_uuid = app.auth._parse_uuid(session_id, "Sessió no vàlida")

    session = (
        db.query(app.models.Session)
        .filter(
            app.models.Session.id == session_uuid,
            app.models.Session.refresh_token == data.refresh_token,
            app.models.Session.is_active,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=401, detail="Sessió no vàlida")

    new_access = app.auth.create_access_token(
        {"sub": str(session.user_id), "sid": str(session.id)}
    )
    return {"access_token": new_access}


@router.post("/logout")
def logout(current=Depends(app.auth.get_current_user), db: Session = Depends(get_db)):
    _user, session = current

    if not session.is_active:
        raise HTTPException(
            status_code=401,
            detail="No hi ha cap sessió activa per tancar",
        )

    session.is_active = False
    db.commit()

    return {"message": "Sessió tancada correctament"}


@router.get("/verify")
def verify(current=Depends(app.auth.get_current_user)):
    user, _session = current

    return {
        "message": "Sessió vàlida",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
        },
    }


@router.post("/forgot-password")
def forgot_password(
    data: app.schemas.ForgotPasswordSchema,
    db: Session = Depends(get_db),
):
    try:
        normalized_email = app.auth.normalize_email(data.email)
    except ValueError as err:
        raise HTTPException(
            status_code=400,
            detail="El format del correu és invàlid",
        ) from err

    user = (
        db.query(app.models.User)
        .filter(
            app.models.User.email_normalized == normalized_email,
            app.models.User.is_active,
        )
        .first()
    )

    if user:
        old_tokens = (
            db.query(app.models.PasswordResetToken)
            .filter(
                app.models.PasswordResetToken.user_id == user.id,
                app.models.PasswordResetToken.used.is_(False),
            )
            .all()
        )

        for old_token in old_tokens:
            old_token.used = True

        reset_token = app.auth.generate_password_reset_token()
        expires_at = app.auth.get_password_reset_expiry()

        token_row = app.models.PasswordResetToken(
            user_id=user.id,
            token=reset_token,
            expires_at=expires_at,
            used=False,
        )

        db.add(token_row)
        db.commit()

        app.auth.send_reset_email(user.email, reset_token)

    return {
        "message": (
            "Si el correu existeix, rebràs instruccions per restablir la contrasenya"
        ),
        "code": "PASSWORD_RESET_REQUEST_ACCEPTED",
    }


@router.post("/change-password")
def change_password(
    data: app.schemas.ChangePasswordSchema,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    current_password, new_password, validation_response = (
        _validate_change_password_input(
            data.current_password,
            data.new_password,
        )
    )

    if validation_response:
        return validation_response

    if not app.auth.verify_password(current_password, user.password_hash):
        return JSONResponse(
            status_code=400,
            content={
                "detail": "La contrasenya actual és incorrecta",
                "code": "CURRENT_PASSWORD_INCORRECT",
            },
        )

    if current_password == new_password:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "La nova contrasenya no pot ser igual que l'actual",
                "code": "NEW_PASSWORD_SAME_AS_CURRENT",
            },
        )

    user.password_hash = app.auth.hash_password(new_password)
    db.commit()

    return {
        "message": "Contrasenya actualitzada correctament",
        "code": "PASSWORD_CHANGED",
    }


@router.post("/reset-password")
def reset_password(
    data: app.schemas.ResetPasswordSchema,
    db: Session = Depends(get_db),
):
    token_row = (
        db.query(app.models.PasswordResetToken)
        .filter(
            app.models.PasswordResetToken.token == data.token,
            app.models.PasswordResetToken.used.is_(False),
        )
        .first()
    )

    if not token_row:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Token invàlid o caducat",
                "code": "RESET_TOKEN_INVALID_OR_EXPIRED",
            },
        )

    if token_row.expires_at < datetime.utcnow():
        token_row.used = True
        db.commit()
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Token invàlid o caducat",
                "code": "RESET_TOKEN_INVALID_OR_EXPIRED",
            },
        )

    user = (
        db.query(app.models.User)
        .filter(
            app.models.User.id == token_row.user_id,
            app.models.User.is_active,
        )
        .first()
    )

    if not user:
        token_row.used = True
        db.commit()
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Token invàlid o caducat",
                "code": "RESET_TOKEN_INVALID_OR_EXPIRED",
            },
        )

    new_password, validation_response = _validate_reset_password_input(
        data.new_password
    )
    if validation_response:
        return validation_response

    user.password_hash = app.auth.hash_password(new_password)
    token_row.used = True

    active_sessions = (
        db.query(app.models.Session)
        .filter(
            app.models.Session.user_id == user.id,
            app.models.Session.is_active,
        )
        .all()
    )

    for session in active_sessions:
        session.is_active = False

    db.commit()

    return {
        "message": "La contrasenya s'ha restablert correctament",
        "code": "PASSWORD_RESET_SUCCESS",
    }


@router.delete("/delete")
def delete_account(
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    user.is_active = False

    old_email_normalized = user.email_normalized
    user.email_normalized = f"deleted::{user.id}::{old_email_normalized}"
    user.email = f"deleted::{user.id}@foodsync.local"
    user.username = f"deleted_{str(user.id)[:8]}"

    sessions = (
        db.query(app.models.Session)
        .filter(
            app.models.Session.user_id == user.id,
            app.models.Session.is_active,
        )
        .all()
    )

    for session in sessions:
        session.is_active = False

    db.commit()

    return {"message": "El teu compte s'ha desactivat correctament"}