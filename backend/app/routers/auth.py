from fastapi import APIRouter, HTTPException, status, Depends, Response, Cookie
from typing import Optional
from app.models.schemas import UserCreate, TokenOut, UserOut
from app.repositories import dynamo
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    set_refresh_cookie, clear_refresh_cookie,
    decode_token, get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_token_out(user: dict, response: Response) -> TokenOut:
    access = create_access_token(user["user_id"], user["username"])
    refresh = create_refresh_token(user["user_id"])
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
    if await dynamo.get_user_by_username(data.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    user = await dynamo.create_user(data.username, hash_password(data.password))
    return _build_token_out(user, response)


@router.post("/login", response_model=TokenOut)
async def login(data: UserCreate, response: Response):
    user = await dynamo.get_user_by_username(data.username)
    if not user or not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return _build_token_out(user, response)


@router.post("/refresh", response_model=TokenOut)
async def refresh(response: Response, refresh_token: Optional[str] = Cookie(default=None)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    payload = decode_token(refresh_token, expected_type="refresh")
    user = await dynamo.get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return _build_token_out(user, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    clear_refresh_cookie(response)


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    user = await dynamo.get_user_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(user_id=user["user_id"], username=user["username"], created_at=user["created_at"])
