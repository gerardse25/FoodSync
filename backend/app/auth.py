import secrets
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session as DBSession

import app.models
from app.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    FRONTEND_RESET_URL,
    PASSWORD_RESET_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
)
from app.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def normalize_email(email: str) -> str:
    email = email.strip().lower()

    if len(email) > 128:
        raise ValueError("El correu no pot superar els 128 caràcters")

    if any(ch.isspace() for ch in email):
        raise ValueError("El correu no pot contenir espais")

    if any(ord(ch) < 32 for ch in email):
        raise ValueError("El correu no pot contenir caràcters de control")

    return email


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire


def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: DBSession = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        session_id = payload.get("sid")
        token_type = payload.get("type")

        if token_type != "access" or not user_id or not session_id:
            raise HTTPException(status_code=401, detail="No autoritzat")

    except JWTError as err:
        raise HTTPException(status_code=401, detail="Sessió caducada") from err

    session = db.query(app.models.Session).filter(
        app.models.Session.id == session_id,
        app.models.Session.user_id == user_id,
        app.models.Session.is_active,
    ).first()

    if not session:
        raise HTTPException(status_code=401, detail="Sessió caducada")

    user = db.query(app.models.User).filter(
        app.models.User.id == user_id,
        app.models.User.is_active,
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="No autoritzat")

    return user, session


def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def get_password_reset_expiry():
    return datetime.utcnow() + timedelta(
        minutes=PASSWORD_RESET_EXPIRE_MINUTES
    )


def build_reset_link(token: str) -> str:
    return f"{FRONTEND_RESET_URL}?token={token}"


def send_reset_email(to_email: str, token: str):
    reset_link = build_reset_link(token)

    body = f"""
Hola,

Has sol·licitat restablir la teva contrasenya de FoodSync.

Fes clic a l'enllaç següent per definir-ne una de nova:
{reset_link}

Aquest enllaç caduca en {PASSWORD_RESET_EXPIRE_MINUTES} minuts.

Si no has fet tu aquesta sol·licitud, pots ignorar aquest correu.
"""

    msg = MIMEText(body)
    msg["Subject"] = "Recuperació de contrasenya - FoodSync"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)