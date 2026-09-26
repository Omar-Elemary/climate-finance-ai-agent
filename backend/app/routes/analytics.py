"""Analytics route — thin: delegates to AnalyticsService (Week 4 adapter)."""
from fastapi import APIRouter, Depends, Path

from backend.app.dependencies import get_analytics_service
from backend.app.schemas import AnalyticsResponse
from backend.app.services.analytics_service import AnalyticsService

router = APIRouter(tags=["analytics"])


@router.get(
    "/discussions/{discussion_id}/analytics",
    response_model=AnalyticsResponse,
    summary="Get discussion analytics",
    response_description=(
        "Week 4 analytics: opinion trajectory, agreement, influence, "
        "sentiment, interaction graph"
    ),
)
def get_analytics(
    discussion_id: str = Path(min_length=1, examples=["test-run-001"]),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsResponse:
    payload = service.get_analytics(discussion_id)
    return AnalyticsResponse(**payload)
