"""Command-line interface for Steampipe MCP server."""

from urllib.parse import urlparse, urlunparse

import click
from mcp.server.fastmcp.utilities.logging import get_logger

# Import tools to ensure they're registered with MCP
from . import tools  # noqa: F401

# Import from local modules
from .server import mcp, settings

logger = get_logger(__name__)


def get_safe_display_url(url: str) -> str:
    """Returns a safe URL for display, with credentials masked."""
    if not url or "://" not in url:
        return "[URL details hidden]"

    try:
        parsed_url = urlparse(url)
        # Create a netloc string with password hidden
        safe_netloc = parsed_url.hostname or ""
        if parsed_url.port:
            safe_netloc += f":{parsed_url.port}"

        if parsed_url.username:
            if parsed_url.password:
                safe_netloc = f"{parsed_url.username}:*****@{safe_netloc}"
            else:
                safe_netloc = f"{parsed_url.username}@{safe_netloc}"

        # Reconstruct the URL without the password for logging
        safe_url_parts = (
            parsed_url.scheme,
            safe_netloc,
            parsed_url.path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment,
        )
        return urlunparse(safe_url_parts)
    except Exception:
        return "[URL details hidden]"


@click.command()
@click.option(
    "--database-url",
    envvar="DATABASE_URL",
    required=True,
    help="PostgreSQL database connection URL (e.g., postgresql://user:pass@host:port/db).",
)
def main(database_url: str) -> None:
    """Starts the Steampipe MCP server."""
    settings.database_url = database_url
    safe_display_url = get_safe_display_url(database_url)
    logger.info(f"Starting Steampipe MCP server for {safe_display_url}...")
    logger.info("Running on stdio...")

    # mcp.run() will now execute with the database_url set above
    mcp.run()  # Defaults to stdio transport


if __name__ == "__main__":
    main()
