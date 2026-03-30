from pydantic import BaseModel, EmailStr, field_validator


class RegisterSchema(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2 or len(value) > 16:
            raise ValueError("El nom d'usuari ha de tenir entre 2 i 16 caràcters")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 6 or len(value) > 32:
            raise ValueError("La contrasenya ha de tenir entre 6 i 32 caràcters")
        return value


class LoginSchema(BaseModel):
    email: EmailStr
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

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if len(value) < 6 or len(value) > 32:
            raise ValueError("La nova contrasenya ha de tenir entre 6 i 32 caràcters")
        return value


class ForgotPasswordSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if len(value) < 6 or len(value) > 32:
            raise ValueError("La nova contrasenya ha de tenir entre 6 i 32 caràcters")
        return value
