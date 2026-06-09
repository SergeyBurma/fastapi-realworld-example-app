from typing import Optional, Union

from app.db.repositories.base import BaseRepository
from app.db.repositories.users import UsersRepository
from app.models.domain.profiles import Profile
from app.models.domain.users import User

UserLike = Union[User, Profile]


class ProfilesRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db)
        self._users_repo = UsersRepository(db)

    async def get_profile_by_username(
        self,
        *,
        username: str,
        requested_user: Optional[UserLike],
    ) -> Profile:
        user = await self._users_repo.get_user_by_username(username=username)

        profile = Profile(username=user.username, bio=user.bio, image=user.image)
        if requested_user:
            profile.following = await self.is_user_following_for_another_user(
                target_user=user,
                requested_user=requested_user,
            )

        return profile

    async def is_user_following_for_another_user(
        self,
        *,
        target_user: UserLike,
        requested_user: UserLike,
    ) -> bool:
        follower = await self._users_repo.get_user_by_username(username=requested_user.username)
        following = await self._users_repo.get_user_by_username(username=target_user.username)

        follow_doc = await self.db.followers.find_one({
            "follower_id": follower.id_,
            "following_id": following.id_,
        })
        return follow_doc is not None

    async def add_user_into_followers(
        self,
        *,
        target_user: UserLike,
        requested_user: UserLike,
    ) -> None:
        follower = await self._users_repo.get_user_by_username(username=requested_user.username)
        following = await self._users_repo.get_user_by_username(username=target_user.username)

        await self.db.followers.insert_one({
            "follower_id": follower.id_,
            "following_id": following.id_,
        })

    async def remove_user_from_followers(
        self,
        *,
        target_user: UserLike,
        requested_user: UserLike,
    ) -> None:
        follower = await self._users_repo.get_user_by_username(username=requested_user.username)
        following = await self._users_repo.get_user_by_username(username=target_user.username)

        await self.db.followers.delete_one({
            "follower_id": follower.id_,
            "following_id": following.id_,
        })
