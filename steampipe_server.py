import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse, urlunparse

import click

# Use psycopg for async postgres access
import psycopg
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.utilities.logging import get_logger

# Import SQL for type hinting with execute
from psycopg import sql as psycopg_sql
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, Field

logger = get_logger(__name__)

class Settings(BaseModel):
    """Settings for the PostgreSQL MCP server."""
    # Make database_url optional initially, it will be set by main()
    database_url: str | None = Field(None,
        description="PostgreSQL database connection URL (e.g., postgresql://user:pass@host:port/db)."
    )

# Create an instance; database_url will be populated later by main()
settings = Settings(database_url=None)

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
        await pool.open(wait=True) # Wait for pool to be ready
        logger.info("Database pool opened.")
        yield {"pool": pool} # Make pool available via context
    finally:
        logger.info("Shutting down and closing database pool...")
        await pool.close()
        logger.info("Database pool closed.")


# --- FastMCP Server Setup ---
mcp = FastMCP(
    "steampipe-mcp",
    dependencies=["psycopg[binary,pool]", "click", "pydantic"],
    lifespan=lifespan,  # Register the lifespan manager
)

# Resource to list available public tables
# @mcp.resource("postgres://db/tables")
# temporary fix to avoid bug with resource validation in mcp
# pending PR https://github.com/modelcontextprotocol/python-sdk/pull/248/files
@mcp.tool()
async def list_all_tables(ctx: Context) -> list[str]:
    """
    Lists all tables in all the schemas in the search_path.
    """
    pool: AsyncConnectionPool = ctx.request_context.lifespan_context["pool"]
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Use psycopg_sql.SQL for literal SQL to help type checkers
                await cur.execute(
                    psycopg_sql.SQL(
                        """
                        WITH search_path_schemas AS (
                          SELECT unnest(string_to_array(current_setting(
                            'search_path'), ', ')) AS schema_name
                        )
                        SELECT
                          CONCAT(t.table_schema, '.', t.table_name)
                        FROM
                          information_schema.tables t
                        JOIN
                          search_path_schemas s ON t.table_schema = s.schema_name
                        WHERE
                          t.table_type IN ('BASE TABLE', 'FOREIGN')
                        ORDER BY
                          t.table_schema;
                        """
                    )
                )
                tables = [row[0] for row in await cur.fetchall()]
                logger.info(f"Found {len(tables)} public tables.")
                return tables
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        raise ValueError(f"Failed to list tables: {e}") from e

@mcp.tool(name="list_tables_in_schema")
async def list_tables_in_schema(
    ctx: Context,
    schema_name: str = Field(..., description="Name of the schema")
) -> list[str]:
    """
    Lists all tables in a specified schema.
    """
    pool: AsyncConnectionPool = ctx.request_context.lifespan_context["pool"]
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Use psycopg_sql.SQL for literal SQL to help type checkers
                await cur.execute(
                    psycopg_sql.SQL(
                        """
                        SELECT
                          CONCAT(t.table_schema, '.', t.table_name)
                        FROM
                          information_schema.tables t
                        WHERE
                          t.table_schema = %s AND
                          t.table_type IN ('BASE TABLE', 'FOREIGN')
                        ORDER BY
                          t.table_schema;
                        """
                    ),
                    (schema_name,),
                )
                tables = [row[0] for row in await cur.fetchall()]
                logger.info(f"Found {len(tables)} public tables.")
                return tables
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        raise ValueError(f"Failed to list tables: {e}") from e

# tool to get the schema for a specific table
@mcp.tool(name="get_table_schema")
async def get_table_schema(
    ctx: Context,
    table_name: str = Field(
        ...,
        description="Name of the table with schema, i.e. public.my_table"
    )
) -> str:
    """
    Gets the column names and data types for a specific table.
    Expects the table name in the format 'schema.table'.
    """
    pool: AsyncConnectionPool = ctx.request_context.lifespan_context["pool"]
    logger.info(f"Fetching schema for table: {table_name}")
    try:
        parts = table_name.split('.', 1) # Split only once
        if len(parts) != 2:
            raise ValueError(
                f"Invalid table name format: '{table_name}'."
                " Expected 'schema.table'.")
        schema, table = parts[0], parts[1]
        logger.debug(f"Parsed schema='{schema}', table='{table}'")
    except Exception as e:
        logger.error(f"Error parsing table name '{table_name}': {e}")
        raise ValueError(
            f"Invalid table name format provided: {table_name}"
        ) from e

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Use parameterized query for safety (already correct here)
                # Use psycopg_sql.SQL for the literal part of the query string
                query_composed = psycopg_sql.SQL(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = {} AND table_schema = {}
                    ORDER BY ordinal_position;
                    """
                ).format(
                    psycopg_sql.Literal(table),
                    psycopg_sql.Literal(schema)
                )
                await cur.execute(
                    query_composed
                )
                columns = await cur.fetchall()
                if not columns:
                    logger.warning(f"Table '{table_name}' not found or has no columns.")
                    raise ValueError(f"Table '{table_name}' not found or is empty.")

                schema_info = [
                    {"column_name": col[0], "data_type": col[1]} for col in columns
                ]
                logger.info(
                    f"Schema fetched for {table_name} with {len(columns)} columns.")
                # Return as a JSON string
                return json.dumps(schema_info, indent=2)
    except psycopg.Error as db_err:
        logger.error(f"Database error fetching schema for {table_name}: {db_err}")
        raise ValueError(f"Database error fetching schema: {db_err}") from db_err
    except Exception as e:
        logger.error(f"Unexpected error fetching schema for {table_name}: {e}")
        raise ValueError(f"Failed to get schema: {e}") from e


@mcp.tool()
async def query(
    ctx: Context,
    sql: str = Field(..., description="Read-only SQL query to execute"),
) -> str:
    """
    Runs a read-only SQL query against the database and returns results as JSON.
    Only SELECT statements are effectively processed due to read-only transaction.
    """
    pool: AsyncConnectionPool = ctx.request_context.lifespan_context["pool"]
    logger.info(f"Executing read-only query: {sql[:100]}...") # Log truncated query

    try:
        async with pool.connection() as conn:
            # Ensure read-only transaction
            # NOTE: If type checkers still complain about readonly/isolation,
            # ensure psycopg stubs are updated or add '# type: ignore[call-arg]'
            async with conn.transaction():
                async with conn.cursor() as cur:
                    # FIX 2: Wrap the raw SQL string with psycopg.sql.SQL
                    #        to satisfy the type checker for cur.execute()
                    await cur.execute(psycopg_sql.SQL(
                        "SET TRANSACTION ISOLATION LEVEL READ COMMITTED"
                    ))
                    await cur.execute(psycopg_sql.SQL(
                        "SET TRANSACTION READ ONLY"
                    ))
                    await cur.execute(sql) # type: ignore[call-arg]
                    # Get column names for better JSON output
                    colnames = [
                        desc.name for desc in cur.description
                    ] if cur.description else []
                    results = await cur.fetchall()
                    rows_as_dicts = [dict(zip(colnames, row)) for row in results]
                    logger.info(
                        f"Query executed successfully, returned {len(results)} rows.")
                    # Use default=str to handle types like datetime
                    # that aren't directly JSON serializable
                    return json.dumps(rows_as_dicts, indent=2, default=str)
    except psycopg.Error as db_err:
        logger.error(f"Database error during query: {db_err}")
        # Provide a more informative error message
        if hasattr(db_err, 'diag'):
            db_error_message = db_err.diag.message_primary
        else:
            db_error_message = str(db_err)
        error_message = (
            f"Database error: {db_error_message}"
        )
        raise ValueError(error_message) from db_err
    except Exception as e:
        logger.error(f"Unexpected error during query: {e}")
        raise ValueError(f"Query execution failed: {e}") from e

@click.command()
@click.option(
    '--database-url',
    envvar='DATABASE_URL',
    required=True,
    help='PostgreSQL database connection URL (e.g., postgresql://user:pass@host:port/db).'
)
def main(database_url: str):
    """Starts the Steampipe MCP server."""

    settings.database_url = database_url
    try:
        parsed_url = urlparse(settings.database_url)
        # Create a netloc string with password hidden
        safe_netloc = parsed_url.hostname or ""
        if parsed_url.username:
            safe_netloc = f"{parsed_url.username}@{safe_netloc}"
            if parsed_url.password:
                safe_netloc = f"{parsed_url.username}:*****@{safe_netloc}"
        if parsed_url.port:
            safe_netloc += f":{parsed_url.port}"

        # Reconstruct the URL without the password for logging
        safe_url_parts = (
            parsed_url.scheme,
            safe_netloc,
            parsed_url.path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment,
        )
        safe_display_url = urlunparse(safe_url_parts)
        logger.info(f"Starting Steampipe MCP server for {safe_display_url}...")
    except Exception: # Fallback in case parsing fails for some reason
        logger.error("Could not parse database URL for safe display.")
        logger.info("Starting Steampipe MCP server (URL details hidden)...")

    logger.info("Running on stdio...")

    # mcp.run() will now execute, and the lifespan manager (if modified)
    # can access the database_url set above.
    mcp.run() # Defaults to stdio transport

if __name__ == "__main__":
    # Remove previous environment/dotenv checks and Pydantic Settings loading logic.
    # Click handles the --database-url option and the DATABASE_URL env var directly.
    main()
