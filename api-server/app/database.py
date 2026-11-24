import ssl
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings


def ssl_setting(root_cert: str | None) -> ssl.SSLContext | bool:
    """asyncpg's ssl argument: off without a CA certificate, verify-ca with one.

    The hostname is not checked, because Data Services Manager supports verify-ca but not
    verify-full for client applications.
    """
    if root_cert is None:
        return False
    context = ssl.create_default_context(cafile=root_cert)
    context.check_hostname = False
    return context


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={"ssl": ssl_setting(settings.database_ssl_root_cert)},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
