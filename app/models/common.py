import datetime

from bson import ObjectId
from pydantic import BaseModel, Field, root_validator, validator


class DateTimeModelMixin(BaseModel):
    created_at: datetime.datetime = None  # type: ignore
    updated_at: datetime.datetime = None  # type: ignore

    @validator("created_at", "updated_at", pre=True)
    def default_datetime(
        cls,  # noqa: N805
        value: datetime.datetime,  # noqa: WPS110
    ) -> datetime.datetime:
        return value or datetime.datetime.now()


class IDModelMixin(BaseModel):
    id_: str = Field(None, alias="id")

    @root_validator(pre=True)
    def map_mongodb_id(cls, values):  # noqa: N805
        if "_id" in values and "id_" not in values:
            v = values["_id"]
            if isinstance(v, ObjectId):
                values["id_"] = str(v)
            else:
                values["id_"] = v
        elif "_id" in values and "id_" in values:
            v = values["_id"]
            if isinstance(v, ObjectId):
                values["id_"] = str(v)
        return values

    @validator("id_", pre=True)
    def convert_id(cls, v):  # noqa: N805
        if isinstance(v, ObjectId):
            return str(v)
        return v

    class Config:
        allow_population_by_field_name = True

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        if "id_" in d:
            d["id"] = d.pop("id_")
        return d

    def json(self, *args, **kwargs):
        return super().json(*args, **kwargs)
