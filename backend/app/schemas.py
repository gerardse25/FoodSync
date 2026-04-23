from pydantic import BaseModel, EmailStr


class RegisterSchema(BaseModel):
    username: str
    email: str
    password: str


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
