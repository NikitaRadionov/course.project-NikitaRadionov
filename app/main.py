import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from sqlalchemy import and_
from sqlmodel import Session, select

from .database import create_db_and_tables, get_session
from .exceptions import ApiError, setup_exception_handlers
from .models import KindEnum, Media, StatusEnum, Token, User
from .schemas import MediaCreate, MediaRead, UserBase, UserCreate

load_dotenv()

if not os.getenv("SECRET_KEY"):
    raise RuntimeError("Missing SECRET_KEY in environment")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


password_hash = PasswordHash.recommended()

app = FastAPI(title="Media Catalog", version="0.1.0")

setup_exception_handlers(app)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


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
            raise ApiError(
                status=401, title="Unauthorized", detail="Invalid authentication"
            )
    except jwt.PyJWTError:
        raise ApiError(
            status=401, title="Unauthorized", detail="Invalid authentication"
        )

    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise ApiError(
            status=401, title="Unauthorized", detail="Invalid authentication"
        )
    return user


@app.post("/users/", response_model=UserBase)
def create_user(user: UserCreate, session: Session = Depends(get_session)):
    db_user = session.exec(select(User).where(User.username == user.username)).first()
    if db_user:
        raise ApiError(status=400, title="Conflict", detail="Username already exists")
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
        raise ApiError(
            status=400,
            title="Invalid Credentials",
            detail="Incorrect username or password",
        )
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
        **media.model_dump(),
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
        raise ApiError(status=404, title="Not Found", detail="Media not found")
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
        raise ApiError(status=404, title="Not Found", detail="Media not found")

    update_fields = new_data.model_dump(exclude_unset=True)
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
        raise ApiError(status=404, title="Not Found", detail="Media not found")
    session.delete(media)
    session.commit()
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def read_root():
    return {
        "service": "Media Catalog API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
