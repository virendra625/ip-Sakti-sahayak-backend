"""Main application entrypoint for IP-SAKTI Sahayak Backend.

Designed for the Smart India Hackathon:
- Modular, well-commented, production-structured FastAPI architecture.
- Full OpenAPI /docs and /redoc support.
- Standardized error handling, CORS, and request tracking.
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import logger, request_id_ctx
from app.api.routes import (
    health,
    chat,
    classification,
    documents,
    sources,
    jurisdictions,
    topics,
    search,
    feedback,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context for startup and shutdown hooks."""
    logger.info("Initializing IP-SAKTI Sahayak backend application...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Embedding Provider: {settings.EMBEDDING_PROVIDER}")

    # Synchronize database schema
    try:
        from app.db.database import init_db
        init_db()
    except Exception as exc:
        logger.error(f"Error initializing database schema: {exc}", exc_info=True)

    # Yield control to the application running state
    yield

    logger.info("Shutting down IP-SAKTI Sahayak backend application...")


def create_application() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.PROJECT_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # 2. Request Tracking & Latency Logging Middleware
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_ctx.set(req_id)
        start_time = time.time()

        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.info(
                f"{request.method} {request.url.path} - Status: {response.status_code} - Latency: {duration_ms}ms"
            )
            response.headers["X-Request-ID"] = req_id
            return response
        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"Unhandled Exception on {request.method} {request.url.path} - Latency: {duration_ms}ms - Error: {str(exc)}",
                exc_info=True,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred while processing the request.",
                        "details": str(exc) if settings.DEBUG else None,
                    },
                },
                headers={"X-Request-ID": req_id},
            )
        finally:
            request_id_ctx.reset(token)

    # 3. Exception Handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        req_id = request_id_ctx.get() or str(uuid.uuid4())
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                },
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = request_id_ctx.get() or str(uuid.uuid4())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request payload or parameters.",
                    "details": exc.errors(),
                },
            },
            headers={"X-Request-ID": req_id},
        )

    # 4. Include Core Routers under API_V1_STR
    app.include_router(health.router, prefix=settings.API_V1_STR)
    app.include_router(chat.router, prefix=settings.API_V1_STR)
    app.include_router(classification.router, prefix=settings.API_V1_STR)
    app.include_router(documents.router, prefix=settings.API_V1_STR)
    app.include_router(sources.router, prefix=settings.API_V1_STR)
    app.include_router(jurisdictions.router, prefix=settings.API_V1_STR)
    app.include_router(topics.router, prefix=settings.API_V1_STR)
    app.include_router(search.router, prefix=settings.API_V1_STR)
    app.include_router(feedback.router, prefix=settings.API_V1_STR)

    return app


app = create_application()
