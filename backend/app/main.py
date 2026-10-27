import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text

from app.api.v1.router import router as api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.db.init_db import create_all, seed_constitutional_articles
from app.db.session import async_session_maker, engine
from app.storage.minio_client import ensure_bucket, get_minio_client


settings = get_settings()
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.env != "production":
        await create_all()
        await seed_constitutional_articles()
        from fastapi.concurrency import run_in_threadpool

        await run_in_threadpool(ensure_bucket)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if settings.enable_docs and settings.env != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.add_middleware(GZipMiddleware, minimum_size=1000)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("http_request", request_id=request_id, method=request.method, path=request.url.path)
        return response

    @application.get("/health", tags=["health"])
    async def health_check() -> dict[str, object]:
        services: dict[str, str] = {}
        try:
            async with async_session_maker() as session:
                await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=2)
            services["database"] = "ok"
        except Exception:
            services["database"] = "unavailable"
        try:
            from redis.asyncio import Redis

            redis = Redis.from_url(
                settings.redis_url,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            await asyncio.wait_for(redis.ping(), timeout=2)
            await redis.aclose()
            services["redis"] = "ok"
        except Exception:
            services["redis"] = "unavailable"
        try:
            from fastapi.concurrency import run_in_threadpool

            await asyncio.wait_for(
                run_in_threadpool(get_minio_client().bucket_exists, settings.minio_bucket),
                timeout=3,
            )
            services["minio"] = "ok"
        except Exception:
            services["minio"] = "unavailable"
        return {"status": "ok" if all(value == "ok" for value in services.values()) else "degraded", "services": services}

    application.include_router(api_router)
    register_exception_handlers(application)
    return application


app = create_app()