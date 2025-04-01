from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from Database.main_db import SessionLocal
from DataClasses.DataClasses import UserCreateDC, TokenDC
from service.AuthService import AuthService
from Dependencies.AuthScheme import optional_oauth2_scheme

router = APIRouter(prefix="/auth", tags=["auth"])
auth_service = AuthService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register", response_model=TokenDC)
def register(user: UserCreateDC, db: Session = Depends(get_db)):
    return auth_service.register_user(user, db)

@router.post("/login", response_model=TokenDC)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user_data = UserCreateDC(email=form_data.username, password=form_data.password)
    return auth_service.login_user(user_data, db)

@router.post("/logout")
def logout(token: str = Depends(optional_oauth2_scheme)):
    auth_service.logout_token(token)
    return {"detail": "Successfully logged out"}

@router.get("/check-token")
def check_token(token: str = Depends(optional_oauth2_scheme)):
    print("==== TOKEN ====")
    print(token)
    try:
        if auth_service.is_token_blacklisted(token):
            return {"valid": False}

        payload = auth_service.decode_token(token)
        if payload.get("sub"):
            return {"valid": True}
        return {"valid": False}
    except Exception:
        return {"valid": False}

@router.get("/admin/users")
def get_all_users(db: Session = Depends(get_db)):
    return auth_service.get_all_users(db)