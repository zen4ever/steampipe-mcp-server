"""Test utilities for Steampipe MCP server."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from psycopg_pool import AsyncConnectionPool

from .server import settings


@asynccontextmanager
async def create_test_pool(
    test_db_url: str
) -> AsyncGenerator[AsyncConnectionPool, None]:
    """Create a test database connection pool for testing.

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

    def __init__(self, pool: AsyncConnectionPool):
        """Initialize with a connection pool.

        Args:
            pool: The AsyncConnectionPool to use in the mock context
        """
        class MockRequestContext:
            def __init__(self, lifespan_context: dict[str, Any]):
                self.lifespan_context = lifespan_context

        self.request_context = MockRequestContext({"pool": pool})


@asynccontextmanager
async def mock_mcp_context(
    pool: AsyncConnectionPool
) -> AsyncGenerator[MockContext, None]:
    """Create a mock MCP context with a database pool for testing tools.

    Args:
        pool: The AsyncConnectionPool to use in the mock context

    Yields:
        A mock context that can be used with tool functions
    """
    mock_ctx = MockContext(pool)
    yield mock_ctx