from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password, hash_password
from app.models.models import User
from app.repositories.user_repository import UserRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.schemas.user_profile import UserProfileUpdate, PasswordChangeRequest


class UserProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.profile_repo = UserProfileRepository(db)
        self.user_repo = UserRepository(db)

    async def get_profile(self, user_id: int):
        profile = await self.profile_repo.get_by_user_id(user_id)
        return profile

    async def upsert_profile(self, user_id: int, payload: UserProfileUpdate):
        profile = await self.profile_repo.get_by_user_id(user_id)
        update_data = payload.model_dump(exclude_unset=True)

        # Normalize empty strings and empty lists to None (skip if creating)
        cleaned: dict = {}
        for key, value in update_data.items():
            if isinstance(value, str):
                cleaned_value = value.strip()
                if cleaned_value == "":
                    continue
                cleaned[key] = cleaned_value
            elif isinstance(value, list):
                filtered = [v for v in value if str(v).strip()]
                if not filtered:
                    continue
                cleaned[key] = filtered
            else:
                if value is None:
                    continue
                cleaned[key] = value

        if profile is None:
            profile = await self.profile_repo.create(
                self.profile_repo.model(user_id=user_id, **cleaned)
            )
            await self.db.commit()
            await self.db.refresh(profile)
        else:
            for key, value in cleaned.items():
                setattr(profile, key, value)
            await self.db.commit()
            await self.db.refresh(profile)
        return profile

    async def change_password(self, user_id: int, payload: PasswordChangeRequest):
        if payload.new_password != payload.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New passwords do not match.",
            )
        user = await self.user_repo.get_by_id(user_id)
        if user is None or not verify_password(payload.old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Old password is incorrect.",
            )
        user.password_hash = hash_password(payload.new_password)
        await self.db.commit()
        await self.db.refresh(user)
        return user
