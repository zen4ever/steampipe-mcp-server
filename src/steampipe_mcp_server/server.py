"""Core MCP server implementation for Steampipe PostgreSQL database."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

# Use psycopg for async postgres access
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.logging import get_logger

# Import SQL for type hinting with execute
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, Field

logger = get_logger(__name__)


class Settings(BaseModel):
    """Settings for the PostgreSQL MCP server."""
    # Make database_url optional initially, it will be set by main()
    database_url: str | None = Field(
        None,
        description="PostgreSQL database connection URL (e.g., postgresql://user:pass@host:port/db)."
    )


# --- Database Connection Pool Management (Lifespan) ---
@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage the async database connection pool."""
    logger.info("Starting up and creating database pool...")
    if settings.database_url is None:
        raise ValueError("Database URL not configured before lifespan startup.")
    # min_size=1 helps keep at least one connection ready
    pool = AsyncConnectionPool(settings.database_url, min_size=1, open=False)
    try:
        await pool.open(wait=True)  # Wait for pool to be ready
        logger.info("Database pool opened.")
        yield {"pool": pool}  # Make pool available via context
    finally:
        logger.info("Shutting down and closing database pool...")
        await pool.close()
        logger.info("Database pool closed.")


# Create a global settings instance
settings = Settings(database_url=None)

# --- FastMCP Server Setup ---
mcp = FastMCP(
    "steampipe-mcp",
    dependencies=["psycopg[binary,pool]", "click", "pydantic"],
    lifespan=lifespan,  # Register the lifespan manager
)
