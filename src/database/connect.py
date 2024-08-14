import contextlib
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.config.config import settings
from src.repository.contacts import ContactDB
from src.repository.users import UserDB


class Database:
    def __init__(self):
        self._engine = create_async_engine(settings.database_url, echo=True)
        self._async_session: async_sessionmaker = async_sessionmaker(autoflush=False, autocommit=False, bind=self._engine, class_=AsyncSession)

    @contextlib.asynccontextmanager
    async def get_session(self):
        async with self._async_session() as session:
            try:
                yield session
            finally:
                await session.close()

    async def get_contact_db(self) -> ContactDB:
        async with self.get_session() as session:
            return ContactDB(session)


    async def get_user_db(self) -> UserDB:
        async with self.get_session() as session:
            return UserDB(session)
