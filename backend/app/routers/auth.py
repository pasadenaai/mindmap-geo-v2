import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status, Depends, Response, Cookie
from typing import Optional
from app.core.config import settings
from app.models.schemas import UserCreate, LoginIn, TokenOut, UserOut
from app.repositories import dynamo
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    set_refresh_cookie, clear_refresh_cookie,
    decode_token, get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])
audit = logging.getLogger("audit")  # structured security events (AU-2/AU-3), shipped to CloudWatch


def _build_token_out(user: dict, response: Response) -> TokenOut:
    access = create_access_token(user["user_id"], user["username"])
    refresh = create_refresh_token(user["user_id"], int(user.get("token_version", 0)))
    set_refresh_cookie(response, refresh)
    return TokenOut(
        access_token=access,
        user=UserOut(
            user_id=user["user_id"],
            username=user["username"],
            created_at=user["created_at"],
        ),
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, response: Response):
    if not settings.allow_registration:
        audit.warning("event=register outcome=denied reason=registration_closed username=%s", data.username)
        raise HTTPException(status_code=403, detail="Registration is disabled")
    if data.username.lower() in data.password.lower():
        raise HTTPException(status_code=422, detail="Password must not contain the username")
    if await dynamo.get_user_by_username(data.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    user = await dynamo.create_user(data.username, hash_password(data.password))
    audit.info("event=register outcome=success user_id=%s", user["user_id"])
    return _build_token_out(user, response)


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, response: Response):
    user = await dynamo.get_user_by_username(data.username)
    now = datetime.now(timezone.utc)
    if user and user.get("locked_until") and datetime.fromisoformat(user["locked_until"]) > now:
        audit.warning("event=login outcome=locked user_id=%s", user["user_id"])
        raise HTTPException(status_code=429, detail="Account temporarily locked. Try again later.")
    if not user or not verify_password(data.password, user["hashed_password"]):
        if user:
            until = (now + timedelta(minutes=settings.lockout_minutes)).isoformat()
            await dynamo.record_login_failure(user["user_id"], settings.max_failed_logins, until)
            audit.warning("event=login outcome=failure user_id=%s", user["user_id"])
        else:
            audit.warning("event=login outcome=failure reason=unknown_user")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.get("failed_logins") or user.get("locked_until"):
        await dynamo.reset_login_failures(user["user_id"])
    audit.info("event=login outcome=success user_id=%s", user["user_id"])
    return _build_token_out(user, response)


@router.post("/refresh", response_model=TokenOut)
async def refresh(response: Response, refresh_token: Optional[str] = Cookie(default=None)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    payload = decode_token(refresh_token, expected_type="refresh")
    user = await dynamo.get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if int(payload.get("ver", 0)) != int(user.get("token_version", 0)):
        audit.warning("event=refresh outcome=revoked user_id=%s", user["user_id"])
        raise HTTPException(status_code=401, detail="Session revoked")
    return _build_token_out(user, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, refresh_token: Optional[str] = Cookie(default=None)):
    """Clear the cookie and revoke all of the caller's refresh tokens server-side."""
    if refresh_token:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
            await dynamo.bump_token_version(payload["sub"])
            audit.info("event=logout outcome=success user_id=%s", payload["sub"])
        except HTTPException:
            pass  # expired/invalid token: nothing to revoke
    clear_refresh_cookie(response)


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    user = await dynamo.get_user_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(user_id=user["user_id"], username=user["username"], created_at=user["created_at"])
