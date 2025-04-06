An MCP server interacting with PostgresSQL database, primarily for use with Steampipe service.

## Prerequisites

### 1. Install Steampipe

**macOS:**
```bash
brew tap turbot/tap
brew install steampipe
```

**Linux:**
```bash
sudo /bin/sh -c "$(curl -fsSL https://steampipe.io/install/steampipe.sh)"
```

**Windows:**
```bash
iwr -useb https://steampipe.io/install/steampipe.ps1 | iex
```

### 2. Start Steampipe Service

Start Steampipe as a background service:
```bash
steampipe service start
```

You can verify the service is running with:
```bash
steampipe service status
```

### 3. Get Database URL

The Steampipe PostgreSQL connection string can be found:

```bash
steampipe service status
```

Look for the `Database URL` in the output, which typically looks like:
```
postgres://steampipe:password@localhost:9193/steampipe
```

You can provide this URL in the `--database-url` argument when running the server:
```
python steampipe_server.py --database-url postgresql://steampipe:password@localhost:9193/steampipe
```

Note: Protocol must be `postgresql://` for the server to work correctly.

### 4. Configuring Environment Variables

You can configure the database connection using an environment variable instead of passing it each time:

1. Create a `.env` file in the project directory with your database URL:
   ```
   DATABASE_URL=postgresql://steampipe:password@localhost:9193/steampipe
   ```

2. The server will automatically load this configuration when starting up.

## Available Tools

This MCP server provides several useful tools for interacting with your PostgreSQL database:

### `query`
Runs a read-only SQL query against the database and returns results as JSON.

### `list_all_tables`
Lists all available tables in all schemas in your database's search path. Steampipe doesn't use `public` schema, there is schema per connection.

### `list_tables_in_schema`
Lists all tables within a specific schema. Useful to limit the amount of tables, especially when working with just one schema.

### `get_table_schema`
Retrieves column names and data types for a specific table, table should be in a format like `schema.table`.

## Installation

1. Create a virtual environment: `uv venv`
2.  Activate the environment (e.g., `source .venv/bin/activate` on Linux/macOS or `.venv\Scripts\activate` on Windows).
3.  Install the dependencies: `uv sync` (or `uv sync --dev` to include development tools).

**How to Run:**

1.  **Development (Recommended):**
    ```bash
    mcp dev steampipe_server.py
    ```
    This will start the server and the MCP Inspector, allowing you to test the `query` tool and read the resources interactively.

2.  **Directly (for stdio):**
    ```bash
    python steampipe_server.py --database-url postgresql://steampipe:password@localhost:9193/steampipe
    # or
    uv run python steampipe_server.py --database-url postgresql://steampipe:password@localhost:9193/steampipe
    ```
    This runs the server using standard input/output, suitable for integration with tools like Claude Desktop (after using `mcp install`).

3.  **Install in Claude Desktop:**
    ```bash
    # Make sure your .env file is present or DATABASE_URL is set
    mcp install steampipe_server.py
    ```
    This will configure Claude Desktop to run your server, making the `query` tools available within Claude.
