from fastapi import APIRouter, Depends

from backend.app.dependencies import get_topics
from backend.app.schemas import TopicResponse

router = APIRouter(tags=["topics"])


@router.get(
    "/topics",
    response_model=list[TopicResponse],
    summary="List discussion topics",
    response_description="Available climate-finance discussion topics/domains",
)
def list_discussion_topics(topics: list[dict] = Depends(get_topics)) -> list[TopicResponse]:
    return [TopicResponse(**t) for t in topics]
