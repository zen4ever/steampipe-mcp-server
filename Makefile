.PHONY: help install dev-install test lint typecheck format clean dev docs build dist

# Define colors for pretty output
BLUE=\033[0;34m
GREEN=\033[0;32m
YELLOW=\033[0;33m
NC=\033[0m # No Color

help:
	@echo "${BLUE}Steampipe MCP Server${NC} - Available commands:"
	@echo ""
	@echo "${GREEN}Basic Commands:${NC}"
	@echo "  make install        Install the package in the current environment"
	@echo "  make dev-install    Install the package in development mode with dev dependencies"
	@echo "  make test           Run all tests"
	@echo "  make lint           Run code linting (ruff)"
	@echo "  make typecheck      Run type checking (pyright)"
	@echo "  make format         Format code with ruff"
	@echo "  make check          Run linting and type checking"
	@echo "  make clean          Clean build artifacts"
	@echo ""
	@echo "${GREEN}Development Commands:${NC}"
	@echo "  make dev            Run the server in development mode with MCP Inspector"
	@echo "  make server         Run the server directly with stdio transport"
	@echo "  make install-mcp    Install the MCP server in Claude Desktop"
	@echo ""
	@echo "${GREEN}Building Commands:${NC}"
	@echo "  make build          Build the package"
	@echo "  make dist           Create distribution packages (sdist and wheel)"

# Installation commands
install:
	@echo "${BLUE}Installing package...${NC}"
	uv pip install -e .

dev-install:
	@echo "${BLUE}Installing package with development dependencies...${NC}"
	uv pip install -e .[dev]
	uv sync --dev

# Testing commands
test:
	@echo "${BLUE}Running tests...${NC}"
	uv run pytest

test-verbose:
	@echo "${BLUE}Running tests with verbose output...${NC}"
	uv run pytest -xvs

# Code quality commands
lint:
	@echo "${BLUE}Running linter...${NC}"
	uv run ruff check src/ tests/

typecheck:
	@echo "${BLUE}Running type checker...${NC}"
	uv run pyright

format:
	@echo "${BLUE}Formatting code...${NC}"
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

check: lint typecheck
	@echo "${GREEN}All checks passed!${NC}"

# Development commands
dev:
	@echo "${BLUE}Starting server in development mode...${NC}"
	mcp dev src/steampipe_mcp_server/cli.py

server:
	@echo "${BLUE}Running server with stdio transport...${NC}"
	@echo "${YELLOW}Note: Make sure STEAMPIPE_MCP_DATABASE_URL environment variable is set${NC}"
	@if [ -z "$$STEAMPIPE_MCP_DATABASE_URL" ]; then \
		echo "${YELLOW}Warning: STEAMPIPE_MCP_DATABASE_URL is not set!${NC}"; \
	fi
	python -m steampipe_mcp_server.cli

install-mcp:
	@echo "${BLUE}Installing MCP server in Claude Desktop...${NC}"
	@echo "${YELLOW}Note: Make sure STEAMPIPE_MCP_DATABASE_URL environment variable is set${NC}"
	@if [ -z "$$STEAMPIPE_MCP_DATABASE_URL" ]; then \
		echo "${YELLOW}Warning: STEAMPIPE_MCP_DATABASE_URL is not set!${NC}"; \
	fi
	mcp install steampipe_mcp_server.cli:main

# Cleanup command
clean:
	@echo "${BLUE}Cleaning build artifacts...${NC}"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .ruff_cache/
	rm -rf .pytest_cache/
	find . -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "*.pyd" -delete

# Build commands
build:
	@echo "${BLUE}Building package...${NC}"
	uv pip install build
	python -m build

dist: clean build
	@echo "${GREEN}Distribution packages created in dist/${NC}"