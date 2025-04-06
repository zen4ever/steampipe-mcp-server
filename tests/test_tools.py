"""Tests for Steampipe MCP utilities."""

import pytest
from steampipe_mcp_server.cli import get_safe_display_url


class TestCLI:
    """Tests for CLI utilities."""
    
    def test_get_safe_display_url(self):
        """Test safe URL display with credentials."""
        # Test with username and password
        url = "postgresql://user:password@localhost:5432/db"
        safe_url = get_safe_display_url(url)
        assert "user:*****@localhost:5432" in safe_url
        assert "password" not in safe_url
        
        # Test with only username
        url = "postgresql://user@localhost:5432/db"
        safe_url = get_safe_display_url(url)
        assert "user@localhost:5432" in safe_url
        
        # Test with no credentials
        url = "postgresql://localhost:5432/db"
        safe_url = get_safe_display_url(url)
        assert "localhost:5432" in safe_url
        
        # Test with scheme but no URL (technically valid but will fail to parse)
        url = "invalid-url"
        safe_url = get_safe_display_url(url)
        assert safe_url == "[URL details hidden]"
        
        # Test with null input
        safe_url = get_safe_display_url("") 
        assert safe_url == "[URL details hidden]"