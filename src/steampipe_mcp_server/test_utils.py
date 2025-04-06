"""Test utilities for Steampipe MCP server."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from psycopg_pool import AsyncConnectionPool

from .database import DatabaseService
from .server import settings


@asynccontextmanager
async def create_test_db_service(
    test_db_url: str,
) -> AsyncGenerator[DatabaseService, None]:
    """Create a test database service for testing.

    Args:
        test_db_url: The database URL to connect to

    Yields:
        A DatabaseService connected to the test database
    """
    settings.database_url = test_db_url
    db_service = DatabaseService(test_db_url, min_size=1)
    try:
        await db_service.connect()
        yield db_service
    finally:
        await db_service.close()


# Keep the old pool-based function for backward compatibility
@asynccontextmanager
async def create_test_pool(
    test_db_url: str,
) -> AsyncGenerator[AsyncConnectionPool, None]:
    """Create a test database connection pool for testing (deprecated).

    Args:
        test_db_url: The database URL to connect to

    Yields:
        An AsyncConnectionPool connected to the test database
    """
    settings.database_url = test_db_url
    pool = AsyncConnectionPool(test_db_url, min_size=1, open=False)
    try:
        await pool.open(wait=True)
        yield pool  # type: ignore
    finally:
        await pool.close()


class MockContext:
    """Mock MCP context for testing."""

    def __init__(self, db_service_or_pool: DatabaseService | AsyncConnectionPool):
        """Initialize with a database service or pool.

        Args:
            db_service_or_pool: The DatabaseService or AsyncConnectionPool to use
        """

        class MockRequestContext:
            def __init__(self, lifespan_context: dict[str, Any]):
                self.lifespan_context = lifespan_context

        # Handle either a DatabaseService or a connection pool
        if isinstance(db_service_or_pool, DatabaseService):
            self.request_context = MockRequestContext(
                {"db_service": db_service_or_pool}
            )
        else:
            # Backward compatibility for old tests
            self.request_context = MockRequestContext({"pool": db_service_or_pool})


@asynccontextmanager
async def mock_mcp_context(
    db_service_or_pool: DatabaseService | AsyncConnectionPool,
) -> AsyncGenerator[MockContext, None]:
    """Create a mock MCP context with a database service for testing tools.

    Args:
        db_service_or_pool: The DatabaseService or connection pool to use

    Yields:
        A mock context that can be used with tool functions
    """
    mock_ctx = MockContext(db_service_or_pool)
    yield mock_ctx
