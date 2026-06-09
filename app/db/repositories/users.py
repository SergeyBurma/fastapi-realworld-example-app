from typing import Optional

from app.db.errors import EntityDoesNotExist
from app.db.repositories.base import BaseRepository
from app.models.domain.users import User, UserInDB


class UsersRepository(BaseRepository):
    async def get_user_by_email(self, *, email: str) -> UserInDB:
        user_row = await self.db.users.find_one({"email": email})
        if user_row:
            return UserInDB(**user_row)
        raise EntityDoesNotExist(f"user with email {email} does not exist")

    async def get_user_by_username(self, *, username: str) -> UserInDB:
        user_row = await self.db.users.find_one({"username": username})
        if user_row:
            return UserInDB(**user_row)
        raise EntityDoesNotExist(f"user with username {username} does not exist")

    async def create_user(
        self,
        *,
        username: str,
        email: str,
        password: str,
    ) -> UserInDB:
        user = UserInDB(username=username, email=email)
        user.change_password(password)

        user_dict = user.dict(exclude={"id_", "hashed_password", "salt"})
        user_dict["salt"] = user.salt
        user_dict["hashed_password"] = user.hashed_password

        await self.db.users.insert_one(user_dict)

        return await self.get_user_by_username(username=username)

    async def update_user(
        self,
        *,
        user: User,
        username: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        bio: Optional[str] = None,
        image: Optional[str] = None,
    ) -> UserInDB:
        user_in_db = await self.get_user_by_username(username=user.username)

        user_in_db.username = username or user_in_db.username
        user_in_db.email = email or user_in_db.email
        user_in_db.bio = bio or user_in_db.bio
        user_in_db.image = image or user_in_db.image
        if password:
            user_in_db.change_password(password)

        update_data = {
            "username": user_in_db.username,
            "email": user_in_db.email,
            "bio": user_in_db.bio,
            "image": user_in_db.image,
        }
        if password:
            update_data["salt"] = user_in_db.salt
            update_data["hashed_password"] = user_in_db.hashed_password

        await self.db.users.update_one(
            {"username": user.username},
            {"$set": update_data},
        )

        return await self.get_user_by_username(username=user_in_db.username)
