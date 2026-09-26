from fastapi import APIRouter

from backend.app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    response_description="Application is healthy",
)
def get_health() -> HealthResponse:
    return HealthResponse(status="ok")
