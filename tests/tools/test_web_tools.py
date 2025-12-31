import pytest
from tools.web.web_inspector import inspect_web_page

# Note: inspect_web_page typically requires a running browser/debugger
# We will mock the subprocess or socket connection

def test_inspect_page_no_connection(mocker):
    """Test graceful failure when browser not connected"""
    # Mock urllib.request.urlopen to raise error
    mocker.patch("urllib.request.urlopen", side_effect=Exception("Connection refused"))
    
    result = inspect_web_page()
    # Should return instructions or error message, not crash
    assert "tarayıcı" in result.lower() or "hata" in result.lower() or "connected" in result.lower()
