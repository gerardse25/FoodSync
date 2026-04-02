from pydantic import BaseModel, EmailStr, field_validator


def _contains_control_characters(value: str) -> bool:
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in value)


def _contains_escape_sequences(value: str) -> bool:
    return "\\n" in value or "\\t" in value or "\\r" in value


def _validate_text(value: str, field_name: str, min_len: int, max_len: int) -> str:
    value = value.strip()

    if not value:
        raise ValueError(f"El camp {field_name} no pot estar buit")

    if len(value) < min_len or len(value) > max_len:
        raise ValueError(
            f"El camp {field_name} ha de tenir entre {min_len} i {max_len} caràcters"
        )

    if _contains_control_characters(value):
        raise ValueError(f"El camp {field_name} no pot contenir caràcters de control")

    if _contains_escape_sequences(value):
        raise ValueError(f"El camp {field_name} no pot contenir seqüències d'escape")

    if any(ch.isspace() for ch in value):
        raise ValueError(f"El camp {field_name} no pot contenir espais interns")

    return value


class RegisterSchema(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        return _validate_text(value, "username", 2, 16)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_text(value, "password", 6, 32)


class LoginSchema(BaseModel):
    email: str
    password: str


class RefreshSchema(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: EmailStr


class VerifyResponse(BaseModel):
    message: str
    user: UserResponse


class ChangePasswordSchema(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordSchema(BaseModel):
    email: str


class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str
