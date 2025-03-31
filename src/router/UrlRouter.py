from fastapi import APIRouter, HTTPException, Depends
from src.Dependencies.AuthScheme import optional_oauth2_scheme
from src.Database.main_db import User
from sqlalchemy.orm import Session

from src.Database.main_db import SessionLocal
from fastapi.responses import RedirectResponse
from src.DataClasses.DataClasses import LongUrlDC, CreateShortUrlDC, ShortUrlDC, ShortUrlStatsDC, UpdateUrlDC
from src.service.UrlService import UrlService
from src.service.AuthService import AuthService

router = APIRouter()
url_service = UrlService()
auth_service = AuthService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_or_none(
    token: str = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_db)
) -> User | None:
    if not token:
        return None
    try:
        return auth_service.get_current_user(token, db)
    except HTTPException:
        return None

@router.post("/links/shorten", response_model=ShortUrlDC)
async def shorten_url(
    create_dto: CreateShortUrlDC,
    user: User = Depends(get_current_user_or_none)
):
    return url_service.make_short_url(create_dto, user)

@router.get("/links/search", response_model=ShortUrlDC)
async def search_by_original_url(original_url: str):
    return url_service.find_by_original_url(original_url)

@router.get("/links/{short_url}")
async def get_full_url(short_url: str):
    long_url = url_service.get_full_url(short_url)
    if not long_url:
        raise HTTPException(status_code=404, detail="URL not found")
    return RedirectResponse(url=long_url, status_code=302)

@router.get("/links/{short_url}/stats", response_model=ShortUrlStatsDC)
async def get_url_stats(short_url: str):
    return url_service.get_short_url_stats(short_url)

@router.delete("/links/{short_url}", response_model=LongUrlDC)
async def delete_url(short_url: str, user: User = Depends(get_current_user_or_none)):
    success = url_service.delete_by_short_url(short_url, user)
    if not success:
        raise HTTPException(status_code=404, detail="URL not found or not allowed")
    return LongUrlDC(url="Deleted")

@router.put("/links/{short_url}", response_model=LongUrlDC)
async def update_url(short_url: str, dto: UpdateUrlDC, user: User = Depends(get_current_user_or_none)):
    updated = url_service.update_long_url(short_url, dto.newUrl, user)
    if not updated:
        raise HTTPException(status_code=404, detail="URL not found or not updated")
    return LongUrlDC(url=dto.newUrl)

@router.get("/admin/dump-db")
async def dump_database():
    return url_service.get_all_urls()

@router.get("/admin/dump-expired")
async def dump_expired_database():
    return url_service.get_all_expired_urls()