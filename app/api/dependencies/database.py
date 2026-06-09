from typing import AsyncGenerator, Callable, Type

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette.requests import Request

from app.db.repositories.base import BaseRepository


def _get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


def get_repository(
    repo_type: Type[BaseRepository],
) -> Callable[[AsyncIOMotorDatabase], BaseRepository]:
    def _get_repo(
        db: AsyncIOMotorDatabase = Depends(_get_db),
    ) -> BaseRepository:
        return repo_type(db)

    return _get_repo
