"""Database service for PostgreSQL operations."""

import json
from typing import Any

import psycopg
from mcp.server.fastmcp.utilities.logging import get_logger
from psycopg import sql as psycopg_sql
from psycopg_pool import AsyncConnectionPool

logger = get_logger(__name__)


class DatabaseService:
    """Service for managing database connections and operations."""

    def __init__(self, database_url: str, min_size: int = 1):
        """Initialize service with database URL.

        Args:
            database_url: PostgreSQL connection string
            min_size: Minimum number of connections to keep in the pool
        """
        self.database_url = database_url
        self.min_size = min_size
        self.pool: AsyncConnectionPool | None = None

    async def connect(self) -> None:
        """Create and open the connection pool."""
        if self.pool is not None:
            logger.warning("Connection pool already exists, not creating a new one.")
            return

        logger.info("Creating database connection pool...")
        self.pool = AsyncConnectionPool(
            self.database_url, min_size=self.min_size, open=False
        )
        await self.pool.open(wait=True)
        logger.info("Database pool opened.")

    async def close(self) -> None:
        """Close the database connection pool."""
        if self.pool is None:
            logger.warning("No connection pool to close.")
            return

        logger.info("Closing database pool...")
        await self.pool.close()
        self.pool = None
        logger.info("Database pool closed.")

    def _check_connection(self) -> AsyncConnectionPool:
        """Check if the connection pool exists."""
        if self.pool is None:
            raise ValueError(
                "Database connection pool not initialized. Call connect() first."
            )
        return self.pool

    async def execute_query(
        self, query: str, params: tuple | None = None
    ) -> list[dict[str, Any]]:
        """Execute a read-only query and return results as a list of dictionaries.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            List of dictionaries, one for each row
        """
        pool = self._check_connection()
        truncated = query[:100] + "..." if len(query) > 100 else query
        logger.info(f"Executing query: {truncated}")

        try:
            async with pool.connection() as conn:
                # Ensure read-only transaction
                async with conn.transaction():
                    async with conn.cursor() as cur:
                        await cur.execute(
                            psycopg_sql.SQL(
                                "SET TRANSACTION ISOLATION LEVEL READ COMMITTED"
                            )
                        )
                        await cur.execute(psycopg_sql.SQL("SET TRANSACTION READ ONLY"))

                        # Execute the query with parameters if provided
                        if params:
                            await cur.execute(query, params)  # type: ignore[call-arg]
                        else:
                            await cur.execute(query)  # type: ignore[call-arg]

                        # Get column names
                        colnames = (
                            [desc.name for desc in cur.description]
                            if cur.description
                            else []
                        )

                        # Fetch results
                        results = await cur.fetchall()

                        # Convert to list of dictionaries
                        rows_as_dicts = [dict(zip(colnames, row)) for row in results]

                        # Log the result count
                        row_count = len(results)
                        logger.info(f"Query executed: {row_count} rows returned.")
                        return rows_as_dicts

        except psycopg.Error as db_err:
            logger.error(f"Database error during query: {db_err}")
            if hasattr(db_err, "diag"):
                db_error_message = db_err.diag.message_primary
            else:
                db_error_message = str(db_err)
            error_message = f"Database error: {db_error_message}"
            raise ValueError(error_message) from db_err
        except Exception as e:
            logger.error(f"Unexpected error during query: {e}")
            raise ValueError(f"Query execution failed: {e}") from e

    async def execute_sql_query(
        self,
        sql_query: psycopg_sql.SQL | psycopg_sql.Composed,
        params: tuple | None = None,
    ) -> list[tuple]:
        """Execute a parameterized SQL query using psycopg_sql composable objects.

        Args:
            sql_query: SQL query to execute as psycopg_sql.SQL object
            params: Additional parameters (beyond those in SQL Composable)

        Returns:
            List of tuples with raw query results
        """
        pool = self._check_connection()
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    if params:
                        await cur.execute(sql_query, params)
                    else:
                        await cur.execute(sql_query)
                    return await cur.fetchall()
        except psycopg.Error as db_err:
            logger.error(f"Database error: {db_err}")
            raise ValueError(f"Database error: {db_err}") from db_err
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise ValueError(f"Query execution failed: {e}") from e

    async def list_all_tables(self) -> list[str]:
        """List all tables in all schemas in the search path.

        Returns:
            List of tables in format schema.table
        """
        sql = psycopg_sql.SQL(
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

        try:
            results = await self.execute_sql_query(sql)
            tables = [row[0] for row in results]
            logger.info(f"Found {len(tables)} tables.")
            return tables
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            raise ValueError(f"Failed to list tables: {e}") from e

    async def list_tables_in_schema(self, schema_name: str) -> list[str]:
        """List all tables in a specific schema.

        Args:
            schema_name: Schema name to query

        Returns:
            List of tables in format schema.table
        """
        sql = psycopg_sql.SQL(
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
        )

        try:
            results = await self.execute_sql_query(sql, (schema_name,))
            tables = [row[0] for row in results]
            logger.info(f"Found {len(tables)} tables in schema {schema_name}.")
            return tables
        except Exception as e:
            logger.error(f"Error listing tables in schema {schema_name}: {e}")
            raise ValueError(f"Failed to list tables: {e}") from e

    async def get_table_schema(self, table_name: str) -> str:
        """Get schema information for a table.

        Args:
            table_name: Table name in format schema.table

        Returns:
            JSON string with column information
        """
        logger.info(f"Fetching schema for table: {table_name}")

        # Parse schema and table
        try:
            parts = table_name.split(".", 1)  # Split only once
            if len(parts) != 2:
                raise ValueError(
                    f"Invalid table name format: '{table_name}'."
                    " Expected 'schema.table'."
                )
            schema, table = parts[0], parts[1]
            logger.debug(f"Parsed schema='{schema}', table='{table}'")
        except Exception as e:
            logger.error(f"Error parsing table name '{table_name}': {e}")
            raise ValueError(f"Invalid table name format provided: {table_name}") from e

        # Query for column information
        query = psycopg_sql.SQL(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = {} AND table_schema = {}
            ORDER BY ordinal_position;
        """
        ).format(psycopg_sql.Literal(table), psycopg_sql.Literal(schema))

        try:
            columns = await self.execute_sql_query(query)
            if not columns:
                logger.warning(f"Table '{table_name}' not found or has no columns.")
                raise ValueError(f"Table '{table_name}' not found or is empty.")

            schema_info = [
                {"column_name": col[0], "data_type": col[1]} for col in columns
            ]
            logger.info(f"Schema fetched for {table_name} with {len(columns)} columns.")
            return json.dumps(schema_info, indent=2)
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            logger.error(f"Error fetching schema for {table_name}: {e}")
            raise ValueError(f"Failed to get schema: {e}") from e
