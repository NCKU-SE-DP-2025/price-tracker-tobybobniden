from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.api.v1.dependencies import get_current_user
from src.api.v1.auth.schemas import UserAuthSchema
from src.api.v1.auth.service import AuthService
from src.core.security import get_password_hash
from src.db.models import User

router = APIRouter(prefix="/users", tags=["auth"])


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = AuthService.authenticate_user(db, form_data.username, form_data.password)
    token = AuthService.create_token(user.username)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register")
async def create_user(user: UserAuthSchema, db: Session = Depends(get_db)):
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/me")
async def read_current_user(user=Depends(get_current_user)):
    return {"username": user.username}