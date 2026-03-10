from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.routers.auth_router import router as auth_router
from app.routers.poi_router import router as poi_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    yield
    await engine.dispose()


app = FastAPI(
    title="POI Game API",
    description="Gamified POI attribution labeling tool for USC IMSC",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(poi_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "healthy", "database": "connected"}
