from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator
import re
from datetime import datetime

class LongUrlDC(BaseModel):
    url: str

class CreateShortUrlDC(BaseModel):
    url: str
    expiresAt: datetime = None
    alias: str = ""

    @field_validator("alias")
    def validate_alias(cls, value):
        if not value:
            return value  # alias необязательный — пустая строка допустима
        if len(value) > 7:
            raise ValueError("Alias must be at most 7 characters long.")
        if not re.fullmatch(r"^[a-zA-Z0-9_]+$", value):
            raise ValueError("Alias can only contain letters, digits and underscores: [a-zA-Z0-9_]")
        return value

class ShortUrlDC(BaseModel):
    url: str

class ShortUrlStatsDC(BaseModel):
    originalUrl: str
    visits: int
    lastTimeUsed: datetime
    createdAt: datetime

class UpdateUrlDC(BaseModel):
    newUrl: str

class UserCreateDC(BaseModel):
    email: EmailStr
    password: str

class TokenDC(BaseModel):
    access_token: str
    token_type: str = "bearer"