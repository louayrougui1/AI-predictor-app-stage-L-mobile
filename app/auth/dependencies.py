import logging
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import api_messages
from app.auth.jwt import verify_jwt_token
from app.auth.models import User
from app.core import database_session

logger = logging.getLogger(__name__)


async def get_current_user(
    access_token: Annotated[str | None, Cookie()] = None,
    session: AsyncSession = Depends(database_session.new_async_session),
) -> User:
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_messages.JWT_ERROR_USER_REMOVED,
        )

    token_payload = verify_jwt_token(access_token)

    user = await session.scalar(select(User).where(User.user_id == token_payload.sub))

    if user is None:
        logger.exception("Current user not found for token payload sub=%s", token_payload.sub)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_messages.JWT_ERROR_USER_REMOVED,
        )
    return user