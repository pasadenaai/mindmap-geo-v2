from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.agent import service
from app.core.security import require_auth

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=service.MAX_QUERY_CHARS)


class AgentAction(BaseModel):
    type: str
    cca2: str


class AgentResult(BaseModel):
    action: AgentAction | None
    message: str


# POST always requires an access token (require_auth), so anonymous callers cannot spend model budget.
@router.post("", response_model=AgentResult, dependencies=[Depends(require_auth)])
async def resolve(body: AgentQuery) -> AgentResult:
    try:
        result = await service.resolve(body.query)
    except service.AgentUnavailable:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Search assistant unavailable")
    return AgentResult(**result)
