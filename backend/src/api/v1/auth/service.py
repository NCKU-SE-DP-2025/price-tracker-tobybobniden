from datetime import timedelta
from sqlalchemy.orm import Session
from src.db.models import User
from src.core.security import verify_password, get_password_hash, create_access_token
from src.core.config import settings
from src.api.v1.auth.exceptions import InvalidCredentialsException, UserAlreadyExistsException


class AuthService:
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> User:
        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsException()
        return user

    @staticmethod
    def register_user(db: Session, username: str, password: str) -> User:
        user = db.query(User).filter(User.username == username).first()
        if user:
            raise UserAlreadyExistsException()
        
        hashed_password = get_password_hash(password)
        new_user = User(username=username, hashed_password=hashed_password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def create_token(username: str) -> str:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return create_access_token(
            data={"sub": username},
            expires_delta=access_token_expires,
        )
