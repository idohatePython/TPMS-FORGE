from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UserRole = Literal["user", "admin"]


class UserRead(BaseModel):
    id: str
    username: str
    role: UserRole


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead