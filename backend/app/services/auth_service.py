"""
Authentication & User Service Layer.
"""
from datetime import timedelta
import secrets
from fastapi import HTTPException, status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.core.logging import logger
from app.models.models import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserLogin, TokenResponse, UserResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, payload: UserCreate) -> UserResponse:
        if await self.user_repo.email_exists(payload.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        user = User(
            name=payload.name,
            email=payload.email.lower(),
            password_hash=hash_password(payload.password),
            role=payload.role or UserRole.user,
            provider="local",
        )
        created = await self.user_repo.create(user)
        # Persist before responding so immediate login after register is reliable.
        await self.db.commit()
        await self.db.refresh(created)
        logger.info("auth.register_success", user_id=created.id, email=created.email)
        return UserResponse.model_validate(created)

    async def login(self, payload: UserLogin) -> TokenResponse:
        user = await self.user_repo.get_by_email(payload.email.lower())
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        token = create_access_token(
            data={"sub": str(user.id), "role": user.role.value},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        logger.info("auth.login_success", user_id=user.id)
        return TokenResponse(
            access_token=token,
            user=UserResponse.model_validate(user),
        )

    async def login_with_google(self, token: str) -> TokenResponse:
        if not settings.GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth is not configured.",
            )

        async with AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": token},
            )

        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token.",
            )

        data = resp.json()
        aud = data.get("aud")
        email = (data.get("email") or "").lower()
        email_verified = data.get("email_verified") in ("true", True)
        name = data.get("name") or email.split("@")[0]
        given_name = data.get("given_name")
        family_name = data.get("family_name")
        picture = data.get("picture")
        locale = data.get("locale")
        google_sub = data.get("sub")

        if aud != settings.GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google token audience mismatch.",
            )

        if not email or not email_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google account email not verified.",
            )

        user = await self.user_repo.get_by_email(email)
        if user is None:
            user = User(
                name=name,
                email=email,
                password_hash=hash_password(secrets.token_urlsafe(32)),
                role=UserRole.user,
                provider="google",
                google_sub=google_sub,
                avatar_url=picture,
                given_name=given_name,
                family_name=family_name,
                locale=locale,
            )
            user = await self.user_repo.create(user)
            logger.info("auth.google_register_success", user_id=user.id, email=user.email)
        else:
            # Update profile fields when logging in with Google
            user.provider = user.provider or "google"
            user.google_sub = user.google_sub or google_sub
            user.avatar_url = user.avatar_url or picture
            user.given_name = user.given_name or given_name
            user.family_name = user.family_name or family_name
            user.locale = user.locale or locale
            await self.db.commit()
            await self.db.refresh(user)

        token = create_access_token(
            data={"sub": str(user.id), "role": user.role.value},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        logger.info("auth.google_login_success", user_id=user.id)
        return TokenResponse(
            access_token=token,
            user=UserResponse.model_validate(user),
        )
