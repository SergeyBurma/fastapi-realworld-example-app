from datetime import datetime
from typing import List, Optional, Sequence

from app.db.errors import EntityDoesNotExist
from app.db.repositories.base import BaseRepository
from app.db.repositories.profiles import ProfilesRepository
from app.db.repositories.tags import TagsRepository
from app.models.domain.articles import Article
from app.models.domain.users import User

AUTHOR_USERNAME_ALIAS = "author_username"
SLUG_ALIAS = "slug"


class ArticlesRepository(BaseRepository):  # noqa: WPS214
    def __init__(self, db):
        super().__init__(db)
        self._profiles_repo = ProfilesRepository(db)
        self._tags_repo = TagsRepository(db)

    async def create_article(
        self,
        *,
        slug: str,
        title: str,
        description: str,
        body: str,
        author: User,
        tags: Optional[Sequence[str]] = None,
    ) -> Article:
        now = datetime.utcnow()
        article_doc = {
            "slug": slug,
            "title": title,
            "description": description,
            "body": body,
            "author_id": author.id_,
            "author_username": author.username,
            "created_at": now,
            "updated_at": now,
        }
        await self.db.articles.insert_one(article_doc)

        if tags:
            await self._tags_repo.create_tags_that_dont_exist(tags=tags)
            await self._link_article_with_tags(slug=slug, tags=tags)

        return await self._get_article_from_db(
            slug=slug,
            requested_user=author,
        )

    async def update_article(
        self,
        *,
        article: Article,
        slug: Optional[str] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Article:
        updated_article = article.copy(deep=True)
        updated_article.slug = slug or updated_article.slug
        updated_article.title = title or article.title
        updated_article.body = body or article.body
        updated_article.description = description or article.description

        update_data = {
            "slug": updated_article.slug,
            "title": updated_article.title,
            "body": updated_article.body,
            "description": updated_article.description,
            "updated_at": datetime.utcnow(),
        }

        await self.db.articles.update_one(
            {"slug": article.slug, "author_id": article.author_id},
            {"$set": update_data},
        )

        return updated_article

    async def delete_article(self, *, article: Article) -> None:
        await self.db.articles.delete_one({
            "slug": article.slug,
            "author_id": article.author_id,
        })
        await self.db.comments.delete_many({"article_slug": article.slug})
        await self.db.favorites.delete_many({"article_slug": article.slug})
        await self.db.article_tags.delete_many({"article_slug": article.slug})

    async def filter_articles(
        self,
        *,
        tag: Optional[str] = None,
        author: Optional[str] = None,
        favorited: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        requested_user: Optional[User] = None,
    ) -> List[Article]:
        query = {}

        if tag:
            article_slugs = [
                t["article_slug"]
                for t in await self.db.article_tags.find({"tag": tag}).to_list(length=1000)
            ]
            if article_slugs:
                query["slug"] = {"$in": article_slugs}
            else:
                query["slug"] = {"$in": []}

        if author:
            author_user = await self._profiles_repo._users_repo.get_user_by_username(
                username=author
            )
            query["author_id"] = author_user.id_

        if favorited:
            favorited_slugs = [
                f["article_slug"]
                for f in await self.db.favorites.find(
                    {"user_id": favorited}
                ).to_list(length=1000)
            ]
            if favorited_slugs:
                existing_slug_query = query.get("slug", {})
                if isinstance(existing_slug_query, dict) and "$in" in existing_slug_query:
                    query["slug"] = {
                        "$in": list(set(existing_slug_query["$in"] + favorited_slugs))
                    }
                else:
                    query["slug"] = {"$in": favorited_slugs}
            else:
                query["slug"] = {"$in": []}

        cursor = self.db.articles.find(query).sort("created_at", -1).skip(offset).limit(limit)
        article_docs = await cursor.to_list(length=1000)

        return [
            await self._get_article_from_db(
                doc=doc,
                requested_user=requested_user,
            )
            for doc in article_docs
        ]

    async def get_articles_for_user_feed(
        self,
        *,
        user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Article]:
        followed_users = await self.db.followers.find(
            {"follower_id": user.id_}
        ).to_list(length=1000)
        followed_ids = [f["following_id"] for f in followed_users]
        followed_ids.append(user.id_)

        cursor = (
            self.db.articles.find({"author_id": {"$in": followed_ids}})
            .sort("created_at", -1)
            .skip(offset)
            .limit(limit)
        )
        article_docs = await cursor.to_list(length=1000)

        return [
            await self._get_article_from_db(
                doc=doc,
                requested_user=user,
            )
            for doc in article_docs
        ]

    async def get_article_by_slug(
        self,
        *,
        slug: str,
        requested_user: Optional[User] = None,
    ) -> Article:
        article_doc = await self.db.articles.find_one({"slug": slug})
        if article_doc:
            return await self._get_article_from_db(
                doc=article_doc,
                requested_user=requested_user,
            )
        raise EntityDoesNotExist(f"article with slug {slug} does not exist")

    async def get_tags_for_article_by_slug(self, *, slug: str) -> List[str]:
        tag_docs = await self.db.article_tags.find({"article_slug": slug}).to_list(length=1000)
        return [t["tag"] for t in tag_docs]

    async def get_favorites_count_for_article_by_slug(self, *, slug: str) -> int:
        return await self.db.favorites.count_documents({"article_slug": slug})

    async def is_article_favorited_by_user(self, *, slug: str, user: User) -> bool:
        fav = await self.db.favorites.find_one({
            "article_slug": slug,
            "user_id": user.id_,
        })
        return fav is not None

    async def add_article_into_favorites(self, *, article: Article, user: User) -> None:
        await self.db.favorites.insert_one({
            "article_slug": article.slug,
            "user_id": user.id_,
        })

    async def remove_article_from_favorites(
        self,
        *,
        article: Article,
        user: User,
    ) -> None:
        await self.db.favorites.delete_one({
            "article_slug": article.slug,
            "user_id": user.id_,
        })

    async def _get_article_from_db(
        self,
        *,
        doc: Optional[dict] = None,
        slug: Optional[str] = None,
        requested_user: Optional[User] = None,
    ) -> Article:
        if doc is None and slug:
            doc = await self.db.articles.find_one({"slug": slug})

        tags = await self.get_tags_for_article_by_slug(slug=doc["slug"])
        favorites_count = await self.get_favorites_count_for_article_by_slug(slug=doc["slug"])

        article = Article(
            id_=str(doc["_id"]),
            slug=doc["slug"],
            title=doc["title"],
            description=doc["description"],
            body=doc["body"],
            author_id=str(doc["author_id"]),
            author=await self._profiles_repo.get_profile_by_username(
                username=doc["author_username"],
                requested_user=requested_user,
            ),
            tags=tags,
            favorites_count=favorites_count,
            favorited=(
                await self.is_article_favorited_by_user(slug=doc["slug"], user=requested_user)
                if requested_user
                else False
            ),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )
        return article

    async def _link_article_with_tags(self, *, slug: str, tags: Sequence[str]) -> None:
        for tag in tags:
            await self.db.article_tags.insert_one({
                "article_slug": slug,
                "tag": tag,
            })
