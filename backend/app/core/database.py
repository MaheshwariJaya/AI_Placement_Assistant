import asyncio
import logging
import time
from typing import AsyncGenerator, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize Async Engine with connection pooling and schema isolation
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=5,
    pool_pre_ping=True,
    connect_args={
        "server_settings": {
            "search_path": f"{settings.DB_SCHEMA},public"
        }
    },
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency providing an isolated transactional AsyncSession."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection() -> Dict[str, Any]:
    """Test PostgreSQL connectivity.
    
    Performs a fast non-blocking TCP socket probe first. If reachable,
    executes a SELECT 1 query via SQLAlchemy async engine.
    """
    start_time = time.perf_counter()

    # Step 1: Fast non-blocking socket pre-flight probe (1.0s timeout)
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(settings.POSTGRES_HOST, settings.POSTGRES_PORT),
            timeout=1.0,
        )
        writer.close()
        await writer.wait_closed()
    except Exception as tcp_err:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(f"PostgreSQL TCP probe failed on {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT} - {tcp_err}")
        return {
            "connected": False,
            "latency_ms": latency_ms,
            "database": settings.POSTGRES_DB,
            "host": settings.POSTGRES_HOST,
            "error": f"Cannot connect to PostgreSQL at {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}. Ensure the service is started.",
        }

    # Step 2: Database authentication and query execution
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            val = result.scalar()
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            if val == 1:
                return {
                    "connected": True,
                    "latency_ms": latency_ms,
                    "database": settings.POSTGRES_DB,
                    "schema": settings.DB_SCHEMA,
                    "host": settings.POSTGRES_HOST,
                    "error": None,
                }
            return {
                "connected": False,
                "latency_ms": latency_ms,
                "database": settings.POSTGRES_DB,
                "schema": settings.DB_SCHEMA,
                "host": settings.POSTGRES_HOST,
                "error": "Unexpected scalar query response from database.",
            }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.warning(f"Database query execution failed: {exc}")
        return {
            "connected": False,
            "latency_ms": latency_ms,
            "database": settings.POSTGRES_DB,
            "schema": settings.DB_SCHEMA,
            "host": settings.POSTGRES_HOST,
            "error": str(exc),
        }
