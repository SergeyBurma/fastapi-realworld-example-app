from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI
from loguru import logger

from app.core.settings.app import AppSettings


async def connect_to_db(app: FastAPI, settings: AppSettings) -> None:
    logger.info("Connecting to MongoDB")

    db_url = str(settings.database_url)
    # Extract database name from URL if present, else use default
    if "/" in db_url.split("?")[0].split("$")[0]:
        db_name = db_url.rsplit("/", 1)[-1].split("?")[0].split("$")[0]
    else:
        db_name = "realworld"
    client = AsyncIOMotorClient(db_url)
    app.state.mongodb_client = client
    app.state.db = client[db_name]

    logger.info("Connection established")


async def close_db_connection(app: FastAPI) -> None:
    logger.info("Closing connection to MongoDB")

    app.state.mongodb_client.close()

    logger.info("Connection closed")
