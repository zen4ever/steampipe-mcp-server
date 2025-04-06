"""Core MCP server implementation for Steampipe PostgreSQL database."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.logging import get_logger
from pydantic import BaseModel, Field

from .database import DatabaseService

logger = get_logger(__name__)


class Settings(BaseModel):
    """Settings for the PostgreSQL MCP server."""

    # Make database_url optional initially, it will be set by main()
    database_url: str | None = Field(
        None,
        description="PostgreSQL database connection URL (e.g., postgresql://user:pass@host:port/db).",
    )


# --- Database Connection Pool Management (Lifespan) ---
@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage the database service during server lifecycle."""
    logger.info("Starting up database service...")
    if settings.database_url is None:
        raise ValueError("Database URL not configured before lifespan startup.")

    # Create database service
    db_service = DatabaseService(settings.database_url, min_size=1)
    try:
        # Connect to the database
        await db_service.connect()
        yield {"db_service": db_service}  # Make database service available via context
    finally:
        logger.info("Shutting down database service...")
        await db_service.close()
        logger.info("Database service closed.")


# Create a global settings instance
settings = Settings(database_url=None)

# --- FastMCP Server Setup ---
mcp = FastMCP(
    "steampipe-mcp",
    dependencies=["psycopg[binary,pool]", "click", "pydantic"],
    lifespan=lifespan,  # Register the lifespan manager
)
