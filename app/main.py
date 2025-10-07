from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import List, Optional

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from pydantic import BaseModel
from sqlalchemy import and_
from sqlmodel import Field, Session, SQLModel, create_engine, select

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class KindEnum(str, Enum):
    movie = "movie"
    course = "course"


class StatusEnum(str, Enum):
    planned = "planned"
    watching = "watching"
    done = "done"


DATABASE_URL = "sqlite:///./media.db"
engine = create_engine(
    DATABASE_URL, echo=True, connect_args={"check_same_thread": False}
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


password_hash = PasswordHash.recommended()


class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str


class UserCreate(UserBase):
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class MediaBase(SQLModel):
    title: str
    kind: KindEnum
    year: int = Field(ge=1888, description="Year of production, not earlier than 1888")
    status: StatusEnum


class Media(MediaBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    one_liner: Optional[str] = None


class MediaCreate(MediaBase):
    pass


class MediaRead(MediaBase):
    id: int
    owner_id: int
    one_liner: Optional[str] = None


app = FastAPI(title="Media Catalog", version="0.1.0")


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Normalize FastAPI HTTPException into our error envelope
    detail = exc.detail if isinstance(exc.detail, str) else "http_error"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": detail}},
    )


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_current_user(
    token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid authentication")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")

    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    return user


@app.post("/users/", response_model=UserBase)
def create_user(user: UserCreate, session: Session = Depends(get_session)):
    db_user = session.exec(select(User).where(User.username == user.username)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user


@app.post("/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(
        {"sub": user.username}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/media/", response_model=MediaRead)
def create_media(
    media: MediaCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    new_media = Media(
        **media.dict(),
        owner_id=current_user.id,
        one_liner=f"Metadata for {media.title}",
    )
    session.add(new_media)
    session.commit()
    session.refresh(new_media)
    return new_media


@app.get("/media/", response_model=List[MediaRead])
def list_media(
    kind: Optional[KindEnum] = None,
    status: Optional[StatusEnum] = None,
    session: Session = Depends(get_session),
):
    query = select(Media)
    filters = []
    if kind:
        filters.append(Media.kind == kind)
    if status:
        filters.append(Media.status == status)
    if filters:
        query = query.where(and_(*filters))
    return session.exec(query).all()


@app.get("/media/{media_id}", response_model=MediaRead)
def get_media(
    media_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    media = session.get(Media, media_id)
    if not media or media.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Media not found")
    return media


@app.put("/media/{media_id}", response_model=MediaRead)
def update_media(
    media_id: int,
    new_data: MediaCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    media = session.get(Media, media_id)
    if not media or media.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Media not found")

    update_fields = new_data.dict(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(media, field, value)

    session.add(media)
    session.commit()
    session.refresh(media)
    return media


@app.delete("/media/{media_id}")
def delete_media(
    media_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    media = session.get(Media, media_id)
    if not media or media.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Media not found")
    session.delete(media)
    session.commit()
    return {"ok": True}
