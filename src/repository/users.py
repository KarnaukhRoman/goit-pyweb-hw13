from abc import ABC, abstractmethod

from fastapi import HTTPException, status
from libgravatar import Gravatar
from sqlalchemy import select, func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.repository.roles import RoleDB
from src.schemas.roles import RoleEnum
from src.schemas.users import UserModel


class UserABC(ABC):
    pass

    @abstractmethod
    async def create_user(self, body) -> User:
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) :
        pass
    @abstractmethod
    async def update_token(self, user: User, token: str):
        pass

class UserDB(UserABC):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session


    async def create_user(self, body: UserModel):
        user_role = await RoleDB(self._session).get_role_by_name(RoleEnum.user.value)
        avatar = None
        try:
            g = Gravatar(body.email)
            avatar = g.get_image()
        except Exception as err:
            print(err)
        new_user = User(**body.model_dump(), avatar=avatar, role_id=user_role.id)
        self._session.add(new_user)
        await self._session.commit()
        await self._session.refresh(new_user)
        return new_user


    async def get_user_by_email(self, email: str):
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


    async def update_token(self, user: User, refresh_token: str | None):
        user.refresh_token = refresh_token
        await self._session.commit()


    async def confirmed_email(self, email: str):
        user = await self.get_user_by_email(email)
        user.confirmed = True
        await self._session.commit()


    async def update_avatar(self, email: str, url_avatar: str | None)-> User:
        user = await self.get_user_by_email(email)
        user.avatar = url_avatar
        await self._session.commit()
        return user

    async def update_password(self, email: str, new_password: str):
        user = await self.get_user_by_email(email)
        user.password = new_password
        await self._session.commit()
        return user