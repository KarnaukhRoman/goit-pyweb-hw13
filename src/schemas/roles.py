from enum import Enum

from pydantic import BaseModel



class RoleEnum(str, Enum):
    admin = "admin"
    moderator = "moderator"
    user = "user"


class RoleBase(BaseModel):
    id: int
    name: RoleEnum

