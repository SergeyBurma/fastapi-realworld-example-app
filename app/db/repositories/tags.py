from typing import List, Sequence

from app.db.repositories.base import BaseRepository


class TagsRepository(BaseRepository):
    async def get_all_tags(self) -> List[str]:
        tags = await self.db.tags.distinct("tag", {})
        return list(tags)

    async def create_tags_that_dont_exist(self, *, tags: Sequence[str]) -> None:
        existing = await self.db.tags.distinct("tag", {"tag": {"$in": list(tags)}})
        new_tags = [{"tag": t} for t in tags if t not in existing]
        if new_tags:
            await self.db.tags.insert_many(new_tags)
