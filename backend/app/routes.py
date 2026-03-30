from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import JWTError

from app.database import get_db
import app.models
import app.schemas
import app.auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: app.schemas.RegisterSchema, db: Session = Depends(get_db)):
    try:
        normalized_email = app.auth.normalize_email(data.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    existing_user = db.query(app.models.User).filter(
        app.models.User.email_normalized == normalized_email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Aquest correu electrònic ja està registrat"
        )

    new_user = app.models.User(
        username=data.username.strip(),
        email=data.email.strip(),
        email_normalized=normalized_email,
        password_hash=app.auth.hash_password(data.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = app.auth.create_access_token({"sub": str(new_user.id)})
    refresh_token, refresh_expire = app.auth.create_refresh_token({"sub": str(new_user.id)})

    session = app.models.Session(
        user_id=new_user.id,
        refresh_token=refresh_token,
        expires_at=refresh_expire,
        is_active=True,
    )
    db.add(session)
    db.commit()

    return {
        "message": "Compte creat correctament",
        "user": {
            "id": str(new_user.id),
            "username": new_user.username,
            "email": new_user.email
        },
        "access_token": access_token,
        "refresh_token": refresh_token
    }


@router.post("/login")
def login(data: app.schemas.LoginSchema, db: Session = Depends(get_db)):
    try:
        normalized_email = app.auth.normalize_email(data.email)
    except ValueError:
        raise HTTPException(status_code=401, detail="Credencials incorrectes")

    user = db.query(app.models.User).filter(
        app.models.User.email_normalized == normalized_email,
        app.models.User.is_active == True
    ).first()

    if not user or not app.auth.verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credencials incorrectes")

    refresh_token, refresh_expire = app.auth.create_refresh_token({"sub": str(user.id)})

    session = app.models.Session(
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=refresh_expire,
        is_active=True
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    access_token = app.auth.create_access_token({
        "sub": str(user.id),
        "sid": str(session.id)
    })

    return {
        "message": "Inici de sessió exitós",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email
        },
        "access_token": access_token,
        "refresh_token": refresh_token
    }

@router.post("/refresh")
def refresh_token(data: app.schemas.RefreshSchema, db: Session = Depends(get_db)):
    try:
        payload = app.auth.decode_token(data.refresh_token)
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if token_type != "refresh" or not user_id:
            raise HTTPException(status_code=401, detail="Token invàlid")

    except JWTError:
        raise HTTPException(status_code=401, detail="Token invàlid")

    session = db.query(app.models.Session).filter(
        app.models.Session.refresh_token == data.refresh_token,
        app.models.Session.is_active == True
    ).first()

    if not session:
        raise HTTPException(status_code=401, detail="Sessió no vàlida")

    new_access = app.auth.create_access_token({"sub": user_id})
    return {"access_token": new_access}


@router.post("/logout")
def logout(current=Depends(app.auth.get_current_user), db: Session = Depends(get_db)):
    _user, session = current

    if not session.is_active:
        raise HTTPException(status_code=401, detail="No hi ha cap sessió activa per tancar")

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
            "email": user.email
        }
    }

@router.post("/forgot-password")
def forgot_password(data: app.schemas.ForgotPasswordSchema, db: Session = Depends(get_db)):
    try:
        normalized_email = app.auth.normalize_email(data.email)
    except ValueError:
        raise HTTPException(status_code=400, detail="El format del correu és invàlid")

    user = db.query(app.models.User).filter(
        app.models.User.email_normalized == normalized_email,
        app.models.User.is_active == True
    ).first()

    # Resposta genèrica sempre, existeixi o no existeixi el correu
    if user:
        # invalidar tokens anteriors no usats del mateix usuari
        old_tokens = db.query(app.models.PasswordResetToken).filter(
            app.models.PasswordResetToken.user_id == user.id,
            app.models.PasswordResetToken.used == False
        ).all()

        for old_token in old_tokens:
            old_token.used = True

        reset_token = app.auth.generate_password_reset_token()
        expires_at = app.auth.get_password_reset_expiry()

        token_row = app.models.PasswordResetToken(
            user_id=user.id,
            token=reset_token,
            expires_at=expires_at,
            used=False
        )

        db.add(token_row)
        db.commit()

        app.auth.send_reset_email(user.email, reset_token)

    return {
        "message": "Si el correu existeix, rebràs instruccions per restablir la contrasenya"
    }

@router.post("/change-password")
def change_password(
    data: app.schemas.ChangePasswordSchema,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db)
):
    user, _session = current

    if not app.auth.verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="La contrasenya actual és incorrecta")

    user.password_hash = app.auth.hash_password(data.new_password)
    db.commit()

    return {"message": "Contrasenya actualitzada correctament"}

@router.post("/reset-password")
def reset_password(data: app.schemas.ResetPasswordSchema, db: Session = Depends(get_db)):
    token_row = db.query(app.models.PasswordResetToken).filter(
        app.models.PasswordResetToken.token == data.token,
        app.models.PasswordResetToken.used == False
    ).first()

    if not token_row:
        raise HTTPException(status_code=400, detail="Token invàlid o caducat")

    if token_row.expires_at < datetime.utcnow():
        token_row.used = True
        db.commit()
        raise HTTPException(status_code=400, detail="Token invàlid o caducat")

    user = db.query(app.models.User).filter(
        app.models.User.id == token_row.user_id,
        app.models.User.is_active == True
    ).first()

    if not user:
        token_row.used = True
        db.commit()
        raise HTTPException(status_code=400, detail="Token invàlid o caducat")

    user.password_hash = app.auth.hash_password(data.new_password)
    token_row.used = True

    # recomanable: tancar sessions actives quan es canvia per reset
    active_sessions = db.query(app.models.Session).filter(
        app.models.Session.user_id == user.id,
        app.models.Session.is_active == True
    ).all()

    for session in active_sessions:
        session.is_active = False

    db.commit()

    return {
        "message": "La contrasenya s'ha restablert correctament"
    }

@router.delete("/delete")
def delete_account(current=Depends(app.auth.get_current_user), db: Session = Depends(get_db)):
    user, _session = current

    user.is_active = False

    # alliberar el correu per permetre un futur registre
    old_email_normalized = user.email_normalized
    user.email_normalized = f"deleted::{user.id}::{old_email_normalized}"
    user.email = f"deleted::{user.id}@foodsync.local"
    user.username = f"deleted_{str(user.id)[:8]}"

    sessions = db.query(app.models.Session).filter(
        app.models.Session.user_id == user.id,
        app.models.Session.is_active == True
    ).all()

    for session in sessions:
        session.is_active = False

    db.commit()

    return {"message": "El teu compte s'ha desactivat correctament"}