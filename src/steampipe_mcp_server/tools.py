"""MCP tools for interacting with PostgreSQL databases."""

from mcp.server.fastmcp import Context
from mcp.server.fastmcp.utilities.logging import get_logger
from pydantic import Field

from .database import DatabaseService
from .server import mcp

logger = get_logger(__name__)


@mcp.tool()
async def list_all_tables(ctx: Context) -> list[str]:
    """
    Lists all tables in all the schemas in the search_path.
    """
    db_service: DatabaseService = ctx.request_context.lifespan_context["db_service"]
    return await db_service.list_all_tables()


@mcp.tool(name="list_tables_in_schema")
async def list_tables_in_schema(
    ctx: Context, schema_name: str = Field(..., description="Name of the schema")
) -> list[str]:
    """
    Lists all tables in a specified schema.
    """
    db_service: DatabaseService = ctx.request_context.lifespan_context["db_service"]
    return await db_service.list_tables_in_schema(schema_name)


@mcp.tool(name="get_table_schema")
async def get_table_schema(
    ctx: Context,
    table_name: str = Field(
        ..., description="Name of the table with schema, i.e. public.my_table"
    ),
) -> str:
    """
    Gets the column names and data types for a specific table.
    Expects the table name in the format 'schema.table'.
    """
    db_service: DatabaseService = ctx.request_context.lifespan_context["db_service"]
    return await db_service.get_table_schema(table_name)


@mcp.tool()
async def query(
    ctx: Context,
    sql: str = Field(..., description="Read-only SQL query to execute"),
) -> str:
    """
    Runs a read-only SQL query against the database and returns results as JSON.
    Only SELECT statements are effectively processed due to read-only transaction.
    """
    db_service: DatabaseService = ctx.request_context.lifespan_context["db_service"]
    results = await db_service.execute_query(sql)

    # The execute_query method returns a list of dictionaries
    # Convert to JSON string with appropriate formatting
    import json

    return json.dumps(results, indent=2, default=str)
