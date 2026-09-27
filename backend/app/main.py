"""FastAPI application factory (Persona 3 owned).

OpenAPI (Swagger UI at /docs) is the primary contract for the frontend team.
"""
from __future__ import annotations

import backend.app  # noqa: F401  (ensures repo-root sys.path bootstrap)
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.errors import BackendError, error_payload
from backend.app.routes import analytics as analytics_route
from backend.app.routes import discussions as discussions_route
from backend.app.routes import health as health_route
from backend.app.routes import topics as topics_route
from backend.app.schemas import ErrorResponse


def create_app() -> FastAPI:
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()

    app = FastAPI(
        title="Qubeterra Climate Finance API",
        description=(
            "Week 5 Backend/API (Persona 3). Stable HTTP boundary over the "
            "Week 1 RAG + Week 3 discussion core and the Week 4 analytics "
            "layer. The frontend must not need RAG/routing/prompt/analytics internals."
        ),
        version="0.1.0",
        responses={500: {"model": ErrorResponse}},
    )

    # Add CORS middleware to allow frontend connections
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # Frontend URL
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )

    app.include_router(health_route.router)
    app.include_router(topics_route.router)
    app.include_router(discussions_route.router)
    app.include_router(analytics_route.router)

    @app.exception_handler(BackendError)
    async def _backend_error_handler(_: Request, exc: BackendError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_payload(
                "VALIDATION_ERROR",
                "Request validation failed.",
                exc.errors(),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        message = str(exc.detail) if exc.detail else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(code, message),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        # Never leak stack traces / internals to API consumers.
        _ = exc
        return JSONResponse(
            status_code=500,
            content=error_payload("INTERNAL_ERROR", "An unexpected error occurred."),
        )

    return app


app = create_app()
