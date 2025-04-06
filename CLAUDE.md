# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Runtime Commands
- Install dependencies: `uv sync` (or `uv sync --dev` for development tools)
- Run server in dev mode: `mcp dev src/steampipe_mcp_server/cli.py`
- Run CLI: `steampipe-mcp --database-url <URL>`
- Install in Claude Desktop: `mcp install steampipe_mcp_server.cli:main`
- Test: `pytest tests`
- Lint: `uv run ruff check src/`
- Type check: `uv run pyright`

## Code Style Guidelines
- Line length: 88 characters
- Python version: >=3.10
- Package structure: src/steampipe_mcp_server/ with modules for server, tools, cli
- Type hints required for all functions and variables
- Use asyncio patterns with psycopg AsyncConnectionPool
- Use mock_mcp_context for testing tools without database
- Import organization: stdlib first, then third-party, then local
- Use psycopg_sql.SQL and parameterized queries for SQL statements
- Error handling: capture exceptions, log details, raise ValueError with context
- Include docstrings for all public functions and classes