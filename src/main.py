from fastapi import FastAPI
from fastapi import Request
from contextlib import asynccontextmanager
import asyncio

from src.router.UrlRouter import router
from src.router.AuthRouter import router as auth_router
from src.Cleaner.cleaner import periodic_expired_cleanup

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запуск фоновой задачи
    task = asyncio.create_task(periodic_expired_cleanup(3600))
    print("[Lifespan] Background cleaner started.")
    yield
    # Здесь можно завершить задачу по shutdown, если надо
    task.cancel()
    print("[Lifespan] Shutting down cleaner.")

app = FastAPI(lifespan=lifespan)

app.include_router(router)
app.include_router(auth_router)