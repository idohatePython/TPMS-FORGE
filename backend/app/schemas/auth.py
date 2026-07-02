from typing import Literal

from pydantic import BaseModel, Field

UserRole = Literal["user", "admin"]


class UserRead(BaseModel):
    id: str
    username: str
    role: UserRole


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(default="", max_length=128)
    role: UserRole = "user"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
