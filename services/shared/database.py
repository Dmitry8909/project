from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def create_engine(database_url: str):
    return create_async_engine(database_url, echo=False, pool_size=100, max_overflow=50)


def create_session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
