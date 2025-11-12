from typing import Optional

from pydantic import ConfigDict, field_validator

from .models import MediaBase, UserBase


class UserCreate(UserBase):
    model_config = ConfigDict(extra="forbid")
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class MediaCreate(MediaBase):
    model_config = ConfigDict(extra="forbid")
    pass


class MediaRead(MediaBase):
    id: int
    owner_id: int
    one_liner: Optional[str] = None
