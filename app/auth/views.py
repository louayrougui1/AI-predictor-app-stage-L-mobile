import logging
import secrets
import time
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import check_rate_limit


from app.auth import api_messages, dependencies
from app.auth.jwt import create_jwt_token
from app.auth.models import RefreshToken, User
from app.auth.password import (
    DUMMY_PASSWORD,
    get_password_hash,
    verify_password,
)
from app.auth.schemas import (
    AccessTokenResponse,
    UserCreateRequest,
    UserResponse,
    UserUpdatePasswordRequest,
)
from app.core.config import get_settings
from app.core.database_session import new_async_session

router = APIRouter(responses=api_messages.UNAUTHORIZED_RESPONSES)
logger = logging.getLogger(__name__)


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    secure = not settings.debug 

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.security.jwt_access_token_expire_secs,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.security.jwt_refresh_token_expire_secs,
        path="/auth",
    )


@router.get("/me", response_model=UserResponse, description="Get current user")
async def read_current_user(
    current_user: User = Depends(dependencies.get_current_user),
) -> User:
    return current_user


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete current user",
)
async def delete_current_user(
    current_user: User = Depends(dependencies.get_current_user),
    session: AsyncSession = Depends(new_async_session),
) -> None:
    await session.execute(delete(User).where(User.user_id == current_user.user_id))
    await session.commit()


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Update current user password",
)
async def reset_current_user_password(
    request: Request,
    user_update_password: UserUpdatePasswordRequest,
    session: AsyncSession = Depends(new_async_session),
    current_user: User = Depends(dependencies.get_current_user),
) -> None:
    await check_rate_limit(
    request,
    str(current_user.user_id),
    ip_limit=30,
    key_limit=5,
    window=60,
)
    current_user.hashed_password = get_password_hash(user_update_password.password)
    session.add(current_user)
    await session.commit()


@router.post(
    "/access-token",
    response_model=AccessTokenResponse,
    responses=api_messages.ACCESS_TOKEN_RESPONSES,
    description="OAuth2 compatible token, sets access/refresh tokens as httpOnly cookies",
)
async def login_access_token(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(new_async_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> AccessTokenResponse:
    await check_rate_limit(
    request,
    form_data.username,
    ip_limit=20,
    key_limit=5,
    window=60,
)
    user = await session.scalar(select(User).where(User.email == form_data.username))

    if user is None:
        verify_password(form_data.password, DUMMY_PASSWORD)
        logger.exception("Failed to authenticate user during login")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.PASSWORD_INVALID,
        )



    if not verify_password(form_data.password, user.hashed_password):
        logger.exception("Failed to authenticate user during login")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.PASSWORD_INVALID,
        )

    jwt_token = create_jwt_token(user_id=user.user_id)

    refresh_token = RefreshToken(
        user_id=user.user_id,
        refresh_token=secrets.token_urlsafe(32),
        exp=int(time.time() + get_settings().security.jwt_refresh_token_expire_secs),
    )
    session.add(refresh_token)
    await session.commit()

    set_auth_cookies(response, jwt_token.access_token, refresh_token.refresh_token)

    return AccessTokenResponse(
        access_token=jwt_token.access_token,
        expires_at=jwt_token.payload.exp,
        refresh_token=refresh_token.refresh_token,
        refresh_token_expires_at=refresh_token.exp,
    )


@router.post(
    "/refresh-token",
    response_model=AccessTokenResponse,
    responses=api_messages.REFRESH_TOKEN_RESPONSES,
    description="Rotate access/refresh tokens using the refresh_token cookie",
)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
    session: AsyncSession = Depends(new_async_session),
) -> AccessTokenResponse:
    
    if refresh_token_cookie is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_messages.REFRESH_TOKEN_NOT_FOUND,
        )
    
    await check_rate_limit(
        request,
        refresh_token_cookie,
        ip_limit=30,
        key_limit=30,
        window=60,
    )
    token = await session.scalar(
        select(RefreshToken)
        .where(RefreshToken.refresh_token == refresh_token_cookie)
        .with_for_update(skip_locked=True)
    )

    if token is None:
        logger.exception("Refresh token was not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.REFRESH_TOKEN_NOT_FOUND,
        )
    elif time.time() > token.exp:
        logger.exception("Refresh token expired")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.REFRESH_TOKEN_EXPIRED,
        )
    elif token.used:
        logger.exception("Refresh token was already used")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.REFRESH_TOKEN_ALREADY_USED,
        )

    token.used = True
    session.add(token)

    jwt_token = create_jwt_token(user_id=token.user_id)

    new_refresh_token = RefreshToken(
        user_id=token.user_id,
        refresh_token=secrets.token_urlsafe(32),
        exp=int(time.time() + get_settings().security.jwt_refresh_token_expire_secs),
    )
    session.add(new_refresh_token)
    await session.commit()

    set_auth_cookies(response, jwt_token.access_token, new_refresh_token.refresh_token)

    return AccessTokenResponse(
        access_token=jwt_token.access_token,
        expires_at=jwt_token.payload.exp,
        refresh_token=new_refresh_token.refresh_token,
        refresh_token_expires_at=new_refresh_token.exp,
    )


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth")
    return {"detail": "Logged out"}


@router.post(
    "/register",
    
    response_model=UserResponse,
    description="Create new user",
    status_code=status.HTTP_201_CREATED,
)
async def register_new_user(
    request: Request,
    new_user: UserCreateRequest,
    session: AsyncSession = Depends(new_async_session),
) -> User:
    await check_rate_limit(
    request,
    new_user.email,
    ip_limit=5,
    key_limit=3,
    window=3600,  # 1 hour
)
    user = await session.scalar(select(User).where(User.email == new_user.email))
    if user is not None:
        logger.exception("Registration failed because the email is already in use")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.EMAIL_ADDRESS_ALREADY_USED,
        )

    user = User(
        username=new_user.username,
        email=new_user.email,
        hashed_password=get_password_hash(new_user.password),
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError:  # pragma: no cover
        await session.rollback()
        logger.exception("Failed to commit user registration due to integrity error")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.EMAIL_ADDRESS_ALREADY_USED,
        )

    return user