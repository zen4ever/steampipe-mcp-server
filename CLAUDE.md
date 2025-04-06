# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Runtime Commands
- Install dependencies: `make dev-install` or `uv pip install -e .[dev]`
- Run server in dev mode: `make dev` or `mcp dev src/steampipe_mcp_server/cli.py`
- Run CLI: `make server` or `steampipe-mcp --database-url <URL>`
- Install in Claude Desktop: `make install-mcp` 
- Test: `make test` or `pytest tests`
- Lint: `make lint` or `uv run ruff check src/`
- Type check: `make typecheck` or `uv run pyright`
- Format code: `make format`
- Run all checks: `make check`

## Project Structure
- `src/steampipe_mcp_server/` - Main package
  - `database.py` - DatabaseService for connection and query handling
  - `server.py` - MCP server setup and lifespan management
  - `tools.py` - MCP tool implementations
  - `cli.py` - Command line interface
- `tests/` - Test directory

## Code Style Guidelines
- Line length: 88 characters
- Python version: >=3.10
- Package structure: src/steampipe_mcp_server/ with modules for server, tools, cli
- Type hints required for all functions and variables
- DatabaseService handles all database connections and query execution
- Use asyncio patterns with psycopg AsyncConnectionPool
- Use mock_mcp_context for testing tools without database
- Import organization: stdlib first, then third-party, then local
- Use psycopg_sql.SQL and parameterized queries for SQL statements
- Error handling: capture exceptions, log details, raise ValueError with context
- Include docstrings for all public functions and classes