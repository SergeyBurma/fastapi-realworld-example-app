from typing import Optional

from app.models.common import IDModelMixin
from app.models.domain.rwmodel import RWModel


class Profile(IDModelMixin, RWModel):
    username: str
    bio: str = ""
    image: Optional[str] = None
    following: bool = False
