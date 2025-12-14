import re
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator
from sqlmodel import Field, SQLModel


class KindEnum(str, Enum):
    movie = "movie"
    course = "course"


class StatusEnum(str, Enum):
    planned = "planned"
    watching = "watching"
    done = "done"


class UserBase(SQLModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(index=True, unique=True)


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class MediaBase(SQLModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=100)
    kind: KindEnum
    year: int = Field(
        ge=1888,
        le=datetime.now().year + 1,
        description="Year of production, not earlier than 1888",
    )
    status: StatusEnum

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if not re.match(r"^[a-zA-Z0-9\s\-_\.!?]+$", v):
            raise ValueError("Title contains invalid characters")
        return v.strip()


class Media(MediaBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    one_liner: Optional[str] = None
