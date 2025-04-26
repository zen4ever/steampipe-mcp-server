# Steampipe MCP Server

An MCP server interacting with PostgreSQL databases, primarily for use with [Steampipe](https://steampipe.io/).

Steampipe has a schema per connection, and creates a search_path that includes all the schemas, but public schema is typically empty. In additiona to that, Steampipe plugins for AWS, GCP and other clouds have a lot of tables, so just listing all of them is not practical. So, the recommended way to prompt your Claude Desktop would be to say something like this: "In steampipe using aws_all schema, give me a list of all ec2 instances". This way Claude will be more likely to use list_tables_in_schema in schema command, to limit the number of tables retrieved.

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
steampipe-mcp-server --database-url postgresql://steampipe:password@localhost:9193/steampipe
```

Note: Protocol must be `postgresql://` for the server to work correctly.

### 4. Configuring Environment Variables

You can configure the database connection using an environment variable instead of passing it each time:

1. Create a `.env` file in the project directory with your database URL:

   ```
   STEAMPIPE_MCP_DATABASE_URL=postgresql://steampipe:password@localhost:9193/steampipe
   ```

2. The server will automatically load this configuration when starting up.

### 5. Install in Claude Desktop

For the published version, you can configure Claude Desktop directly:

1. Open Claude Desktop
2. Navigate to Settings > Developer > Edit Config
3. Add the following configuration to the JSON file:

```json
{
  "mcpServers": {
    "steampipe": {
      "command": "uvx",
      "args": [
        "steampipe-mcp-server",
        "--database-url",
        "postgresql://steampipe:password@localhost:9193/steampipe"
      ]
    }
  }
}
```

4. Save the config file and restart Claude Desktop

Replace the database URL with your actual Steampipe database URL. This configuration uses `uvx` to execute the published package directly.

The tools will be available within Claude under the `steampipe` namespace.

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

### Development Setup (Recommended)

The easiest way to get started is to use the included Makefile:

```bash
# Create a virtual environment first
uv venv

# Install development dependencies
make dev-install

# View all available commands
make help
```

Alternatively, you can:

1. Clone the repository
2. Create a virtual environment: `uv venv`
3. Activate the environment: `source .venv/bin/activate` (Linux/macOS) or `.venv\Scripts\activate` (Windows)
4. Install dev dependencies: `uv pip install -e .[dev]`

## Development

### Using the Makefile

The project includes a Makefile with common tasks:

```bash
# Run the server in development mode with Inspector
make dev

# Run tests
make test

# Run linting
make lint

# Run type checking
make typecheck

# Format code
make format

# Run all checks (lint and typecheck)
make check

# Install in Claude Desktop
make install-mcp
```

Run `make help` to see all available commands.

## How to Run

### 1. Development Mode (Recommended)

```bash
# Using make
make dev

# OR manually
mcp dev src/steampipe_mcp_server/cli.py
```

This will start the server and the MCP Inspector, allowing you to test the `query` tool and other tools interactively.

### 2. Using CLI

After installation:

```bash
# Using make
make server

# OR with explicit URL
steampipe-mcp-server --database-url postgresql://steampipe:password@localhost:9193/steampipe

# OR with environment variable
export STEAMPIPE_MCP_DATABASE_URL=postgresql://steampipe:password@localhost:9193/steampipe
steampipe-mcp-server
```

## Testing

Run tests with:

```bash
# Using make
make test

# OR manually
pytest
```

For tests that require a database connection, set the `TEST_DB_URL` environment variable.

## Contributing

1. Fork the repository
2. Create a new branch for your feature
3. Make your changes
4. Run tests and checks: `make check test`
5. Submit a pull request

## Releasing

To release a new version of the package:

1. Update the version in `pyproject.toml`
2. Run all checks to ensure everything is working:

   ```bash
   make check test
   ```

3. Tag the release on GitHub:

   ```bash
   git tag v0.1.0  # Use appropriate version number
   git push origin v0.1.0
   ```
