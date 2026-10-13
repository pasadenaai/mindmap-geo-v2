from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.assistant import service
from app.core.security import require_auth

router = APIRouter(prefix="/assistant", tags=["assistant"])


class AssistantQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=service.MAX_QUERY_CHARS)


class AssistantAction(BaseModel):
    type: str
    cca2: str


class AssistantResult(BaseModel):
    action: AssistantAction | None
    message: str


# POST always requires an access token (require_auth), so anonymous callers cannot spend model budget.
@router.post("", response_model=AssistantResult, dependencies=[Depends(require_auth)])
async def resolve(body: AssistantQuery) -> AssistantResult:
    try:
        result = await service.resolve(body.query)
    except service.AssistantUnavailable:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Search assistant unavailable")
    return AssistantResult(**result)
