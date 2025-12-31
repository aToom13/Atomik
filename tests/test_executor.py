import pytest
from tools.executor import execute_tool
from tools.declarations import get_declarations

def test_declarations_load():
    """Test that tool declarations are loaded correctly"""
    decs = get_declarations()
    assert len(decs) > 0
    # Check for a known tool
    names = [d["name"] for d in decs]
    assert "get_current_time" in names
    assert "list_files" in names

def test_execute_basic_tool():
    """Test executing a basic tool"""
    # get_current_time usually returns a string with date
    result = execute_tool("get_current_time", {})
    assert "20" in result  # Should contain year 20xx
    assert ":" in result   # Should contain time

def test_execute_unknown_tool():
    """Test error handling for unknown tool"""
    result = execute_tool("unknown_tool_xyz", {})
    # "Unknown tool" or "Bilinmeyen araç" depending on locale/implementation
    assert "unknown tool" in result.lower() or "bilinmiyor" in result.lower()

def test_execute_tool_with_args():
    """Test tool with arguments (write_file/read_file)"""
    import os
    
    # Use a file inside 'atom_workspace' directory to satisfy workspace restriction
    workspace_dir = os.path.abspath("atom_workspace")
    os.makedirs(workspace_dir, exist_ok=True)
    
    test_file = os.path.join(workspace_dir, "test_exec_artifact.txt")
    
    try:
        # Write
        res_write = execute_tool("write_file", {"filename": test_file, "content": "Hello World"})
        # Check for success message
        assert any(x in res_write.lower() for x in ["oluşturuldu", "yazıldı", "created", "success"])
        
        # Read
        res_read = execute_tool("read_file", {"filename": test_file})
        assert "Hello World" in res_read
        
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
