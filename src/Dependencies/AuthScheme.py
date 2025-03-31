from fastapi.security import OAuth2PasswordBearer

optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)