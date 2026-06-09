from motor.motor_asyncio import AsyncIOMotorDatabase


class BaseRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db
