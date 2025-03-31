import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext

from src.Database.main_db import User
from src.DataClasses.DataClasses import UserCreateDC, TokenDC
from src.Database.redis import get_redis_client

class AuthService:
    SECRET_KEY = "your_secret_key"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

    def __init__(self):
        self.redis = get_redis_client()

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
        to_encode.update({
            "exp": expire,
            "jti": str(uuid.uuid4())  # уникальный идентификатор токена
        })
        return jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)

    def register_user(self, user_data: UserCreateDC, db: Session) -> TokenDC: 
        user = User(email=user_data.email, password_hash=self.hash_password(user_data.password))
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Email already registered")

        token = self.create_access_token({"sub": user.email})
        return TokenDC(access_token=token)

    def login_user(self, user_data: UserCreateDC, db: Session) -> TokenDC:
        user = db.query(User).filter(User.email == user_data.email).first()
        if not user or not self.verify_password(user_data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = self.create_access_token({"sub": user.email})
        return TokenDC(access_token=token)
    
    def get_current_user(self, token: str, db: Session) -> User:
        if self.is_token_blacklisted(token):
            raise HTTPException(status_code=401, detail="Token is blacklisted (logged out)")

        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise HTTPException(status_code=401, detail="Invalid token")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def logout_token(self, token: str):
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            exp = payload.get("exp")
            ttl = exp - int(datetime.now(timezone.utc).timestamp())
            self.redis.set(f"blacklist:{token}", "true", ex=ttl)
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    def is_token_blacklisted(self, token: str) -> bool:
        return self.redis.exists(f"blacklist:{token}") == 1
    
    def decode_token(self, token: str) -> dict:
        return jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])

    def get_all_users(self, db: Session) -> list[dict]:
        users = db.query(User).all()
        return [
            {
                "id": u.id,
                "email": u.email,
                "isActive": u.is_active,
                "createdAt": u.created_at
            }
            for u in users
        ]
