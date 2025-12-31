"""
Tests for MCP Client Module
"""
import pytest
import asyncio
import json
from pathlib import Path


class TestMCPClientManager:
    """Tests for MCPClientManager class"""
    
    def test_import(self):
        """Test that MCP module can be imported"""
        try:
            from mcp_client import MCPClientManager, get_mcp_manager
            assert MCPClientManager is not None
            assert get_mcp_manager is not None
        except ImportError as e:
            pytest.skip(f"MCP SDK not installed: {e}")
    
    def test_singleton(self):
        """Test that get_mcp_manager returns singleton"""
        try:
            from mcp_client import get_mcp_manager
            manager1 = get_mcp_manager()
            manager2 = get_mcp_manager()
            assert manager1 is manager2
        except ImportError:
            pytest.skip("MCP SDK not installed")
    
    def test_config_path(self):
        """Test that config path resolves correctly"""
        try:
            from mcp_client import MCPClientManager
            manager = MCPClientManager()
            assert manager.config_path.name == "servers.json"
            assert manager.config_path.parent.name == "mcp_client"
        except ImportError:
            pytest.skip("MCP SDK not installed")
    
    def test_empty_config(self):
        """Test loading empty servers config"""
        try:
            from mcp_client import MCPClientManager
            
            # Create manager with test config
            manager = MCPClientManager()
            
            # Check that servers.json exists and is valid
            if manager.config_path.exists():
                config = json.loads(manager.config_path.read_text())
                assert "mcpServers" in config
        except ImportError:
            pytest.skip("MCP SDK not installed")


class TestMCPToolExecution:
    """Tests for MCP tool execution in executor"""
    
    def test_mcp_tool_format_detection(self):
        """Test that mcp:server:tool format is detected"""
        from tools.executor import execute_tool
        
        # Test with invalid format
        result = execute_tool("mcp:invalid", {})
        assert "Invalid MCP tool format" in result
    
    def test_mcp_unconnected_server(self):
        """Test calling tool on unconnected server"""
        try:
            from mcp_client import MCPClientManager
            
            manager = MCPClientManager()
            
            # Try calling tool on non-existent server
            result = asyncio.run(manager.call_tool("nonexistent", "test", {}))
            assert "not connected" in result
        except ImportError:
            pytest.skip("MCP SDK not installed")


class TestMCPConfig:
    """Tests for MCP configuration"""
    
    def test_servers_json_exists(self):
        """Test that servers.json configuration file exists"""
        config_path = Path(__file__).parent.parent / "mcp_client" / "servers.json"
        assert config_path.exists(), f"Config not found at {config_path}"
    
    def test_servers_json_valid(self):
        """Test that servers.json is valid JSON"""
        config_path = Path(__file__).parent.parent / "mcp_client" / "servers.json"
        if config_path.exists():
            config = json.loads(config_path.read_text())
            assert isinstance(config, dict)
            assert "mcpServers" in config
