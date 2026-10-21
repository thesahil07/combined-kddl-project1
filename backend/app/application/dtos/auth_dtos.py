"""Authentication DTOs."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=150)
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL.fullmatch(value):
            raise ValueError("invalid email")
        return value


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not any(character.islower() for character in value):
            raise ValueError("must include a lowercase letter")
        if not any(character.isupper() for character in value):
            raise ValueError("must include an uppercase letter")
        if not any(character.isdigit() for character in value):
            raise ValueError("must include a number")
        return value
