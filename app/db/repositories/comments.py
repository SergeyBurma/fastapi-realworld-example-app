from datetime import datetime
from typing import List, Optional

from app.db.errors import EntityDoesNotExist
from app.db.repositories.base import BaseRepository
from app.db.repositories.profiles import ProfilesRepository
from app.models.domain.articles import Article
from app.models.domain.comments import Comment
from app.models.domain.users import User


class CommentsRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db)
        self._profiles_repo = ProfilesRepository(db)

    async def get_comment_by_id(
        self,
        *,
        comment_id: str,
        article: Article,
        user: Optional[User] = None,
    ) -> Comment:
        comment_doc = await self.db.comments.find_one({
            "_id": comment_id,
            "article_slug": article.slug,
        })
        if comment_doc:
            return await self._get_comment_from_db(
                doc=comment_doc,
                requested_user=user,
            )
        raise EntityDoesNotExist(f"comment with id {comment_id} does not exist")

    async def get_comments_for_article(
        self,
        *,
        article: Article,
        user: Optional[User] = None,
    ) -> List[Comment]:
        comments_docs = await self.db.comments.find(
            {"article_slug": article.slug}
        ).sort("created_at", -1).to_list(length=1000)

        return [
            await self._get_comment_from_db(
                doc=doc,
                requested_user=user,
            )
            for doc in comments_docs
        ]

    async def create_comment_for_article(
        self,
        *,
        body: str,
        article: Article,
        user: User,
    ) -> Comment:
        now = datetime.utcnow()
        comment_doc = {
            "body": body,
            "author_id": user.id_,
            "author_username": user.username,
            "article_slug": article.slug,
            "created_at": now,
            "updated_at": now,
        }
        result = await self.db.comments.insert_one(comment_doc)
        comment_doc["_id"] = result.inserted_id

        return await self._get_comment_from_db(
            doc=comment_doc,
            requested_user=user,
        )

    async def delete_comment(self, *, comment: Comment) -> None:
        await self.db.comments.delete_one({
            "_id": comment.id_,
            "author_id": comment.author.id_,
        })

    async def _get_comment_from_db(
        self,
        *,
        doc: dict,
        requested_user: Optional[User] = None,
    ) -> Comment:
        return Comment(
            id_=str(doc["_id"]),
            body=doc["body"],
            author=await self._profiles_repo.get_profile_by_username(
                username=doc["author_username"],
                requested_user=requested_user,
            ),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )
