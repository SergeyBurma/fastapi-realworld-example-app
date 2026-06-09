from os import environ

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient
from mongomock import MongoClient

from app.db.repositories.articles import ArticlesRepository
from app.db.repositories.users import UsersRepository
from app.models.domain.articles import Article
from app.models.domain.users import UserInDB
from app.services import jwt

environ["APP_ENV"] = "test"


@pytest.fixture
def app() -> FastAPI:
    from app.main import get_application

    return get_application()


@pytest.fixture
def mongomock_client():
    return MongoClient()


@pytest.fixture
async def initialized_app(app: FastAPI, mongomock_client) -> FastAPI:
    async with LifespanManager(app):
        app.state.mongodb_client = mongomock_client
        app.state.db = mongomock_client.get_default_database()
        yield app


@pytest.fixture
async def client(initialized_app: FastAPI) -> AsyncClient:
    async with AsyncClient(
        app=initialized_app,
        base_url="http://testserver",
        headers={"Content-Type": "application/json"},
    ) as client:
        yield client


@pytest.fixture
def authorization_prefix() -> str:
    from app.core.config import get_app_settings

    settings = get_app_settings()
    jwt_token_prefix = settings.jwt_token_prefix

    return jwt_token_prefix


@pytest.fixture
async def test_user(initialized_app: FastAPI) -> UserInDB:
    db = initialized_app.state.db
    return await UsersRepository(db).create_user(
        email="test@test.com", password="password", username="username"
    )


@pytest.fixture
async def test_article(test_user: UserInDB, initialized_app: FastAPI) -> Article:
    db = initialized_app.state.db
    articles_repo = ArticlesRepository(db)
    return await articles_repo.create_article(
        slug="test-slug",
        title="Test Slug",
        description="Slug for tests",
        body="Test " * 100,
        author=test_user,
        tags=["tests", "testing", "pytest"],
    )


@pytest.fixture
def token(test_user: UserInDB) -> str:
    return jwt.create_access_token_for_user(test_user, environ["SECRET_KEY"])


@pytest.fixture
def authorized_client(
    client: AsyncClient, token: str, authorization_prefix: str
) -> AsyncClient:
    client.headers = {
        "Authorization": f"{authorization_prefix} {token}",
        **client.headers,
    }
    return authorized_client
