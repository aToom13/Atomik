#!/usr/bin/env python3

# This script connect the MCP AI agent to Kali Linux terminal and API Server.

# some of the code here was inspired from https://github.com/whit3rabbit0/project_astro , be sure to check them out

import sys
import os
import argparse
import logging
from typing import Dict, Any, Optional
import requests

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_KALI_SERVER = "http://localhost:5000" # change to your linux IP
DEFAULT_REQUEST_TIMEOUT = 1200  # 20 minutes default timeout for API requests

class KaliToolsClient:
    """Client for communicating with the Kali Linux Tools API Server"""
    
    def __init__(self, server_url: str, timeout: int = DEFAULT_REQUEST_TIMEOUT):
        """
        Initialize the Kali Tools Client
        
        Args:
            server_url: URL of the Kali Tools API Server
            timeout: Request timeout in seconds
        """
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        logger.info(f"Initialized Kali Tools Client connecting to {server_url}")
        
    def safe_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform a GET request with optional query parameters.
        
        Args:
            endpoint: API endpoint path (without leading slash)
            params: Optional query parameters
            
        Returns:
            Response data as dictionary
        """
        if params is None:
            params = {}

        url = f"{self.server_url}/{endpoint}"

        try:
            logger.debug(f"GET {url} with params: {params}")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}", "success": False}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}", "success": False}

    def safe_post(self, endpoint: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a POST request with JSON data.
        
        Args:
            endpoint: API endpoint path (without leading slash)
            json_data: JSON data to send
            
        Returns:
            Response data as dictionary
        """
        url = f"{self.server_url}/{endpoint}"
        
        try:
            logger.debug(f"POST {url} with data: {json_data}")
            response = requests.post(url, json=json_data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}", "success": False}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}", "success": False}

    def execute_command(self, command: str) -> Dict[str, Any]:
        """
        Execute a generic command on the Kali server
        
        Args:
            command: Command to execute
            
        Returns:
            Command execution results
        """
        return self.safe_post("api/command", {"command": command})
    
    def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the Kali Tools API Server
        
        Returns:
            Health status information
        """
        return self.safe_get("health")

# Initialize MCP Server globally
mcp = FastMCP("kali-mcp")

# Global client holder (will be set in main)
_kali_client: Optional[KaliToolsClient] = None

@mcp.tool(name="nmap_scan")
def nmap_scan(target: str, scan_type: str = "-sV", ports: str = "", additional_args: str = "") -> Dict[str, Any]:
    """Execute an Nmap scan against a target."""
    if not _kali_client: return {"error": "Kali Client not initialized"}
    data = {"target": target, "scan_type": scan_type, "ports": ports, "additional_args": additional_args}
    return _kali_client.safe_post("api/tools/nmap", data)

# @mcp.tool(name="gobuster_scan")
def gobuster_scan(url: str, mode: str = "dir", wordlist: str = "/usr/share/wordlists/dirb/common.txt", additional_args: str = "") -> Dict[str, Any]:
    """Execute Gobuster to find directories, DNS subdomains, or virtual hosts."""
    if not _kali_client: return {"error": "Kali Client not initialized"}
    data = {"url": url, "mode": mode, "wordlist": wordlist, "additional_args": additional_args}
    return _kali_client.safe_post("api/tools/gobuster", data)

# @mcp.tool(name="dirb_scan")
def dirb_scan(url: str, wordlist: str = "/usr/share/wordlists/dirb/common.txt", additional_args: str = "") -> Dict[str, Any]:
    """Execute Dirb web content scanner."""
    if not _kali_client: return {"error": "Kali Client not initialized"}
    data = {"url": url, "wordlist": wordlist, "additional_args": additional_args}
    return _kali_client.safe_post("api/tools/dirb", data)

# @mcp.tool(name="nikto_scan")
def nikto_scan(target: str, additional_args: str = "") -> Dict[str, Any]:
    """Execute Nikto web server scanner."""
    if not _kali_client: return {"error": "Kali Client not initialized"}
    data = {"target": target, "additional_args": additional_args}
    return _kali_client.safe_post("api/tools/nikto", data)

# @mcp.tool(name="sqlmap_scan")
def sqlmap_scan(url: str, data: str = "", additional_args: str = "") -> Dict[str, Any]:
    """Execute SQLmap SQL injection scanner."""
    if not _kali_client: return {"error": "Kali Client not initialized"}
    post_data = {"url": url, "data": data, "additional_args": additional_args}
    return _kali_client.safe_post("api/tools/sqlmap", post_data)

@mcp.tool(name="metasploit_run")
def metasploit_run(module: str, options: Dict[str, Any] = {}) -> Dict[str, Any]:
    """Execute a Metasploit module."""
    if not _kali_client: return {"error": "Kali Client not initialized"}
    data = {"module": module, "options": options}
    return _kali_client.safe_post("api/tools/metasploit", data)

# @mcp.tool(name="hydra_attack")
def hydra_attack(target: str, service: str, username: str = "", username_file: str = "", password: str = "", password_file: str = "", additional_args: str = "") -> Dict[str, Any]:
    """Execute Hydra password cracking tool."""
    if not _kali_client: return {"error": "Kali Client not initialized"}
    data = {"target": target, "service": service, "username": username, "username_file": username_file, "password": password, "password_file": password_file, "additional_args": additional_args}
    return _kali_client.safe_post("api/tools/hydra", data)

# @mcp.tool(name="john_crack")
def john_crack(hash_file: str, wordlist: str = "/usr/share/wordlists/rockyou.txt", format_type: str = "", additional_args: str = "") -> Dict[str, Any]:
    """Execute John the Ripper password cracker."""
    if not _kali_client: return {"error": "Kali Client not initialized"}
    data = {"hash_file": hash_file, "wordlist": wordlist, "format": format_type, "additional_args": additional_args}
    return _kali_client.safe_post("api/tools/john", data)

# @mcp.tool(name="wpscan_analyze")
def wpscan_analyze(url: str, additional_args: str = "") -> Dict[str, Any]:
    """Execute WPScan WordPress vulnerability scanner."""
    if not _kali_client: return {"error": "Kali Client not initialized"}
    data = {"url": url, "additional_args": additional_args}
    return _kali_client.safe_post("api/tools/wpscan", data)

# @mcp.tool(name="enum4linux_scan")
def enum4linux_scan(target: str, additional_args: str = "-a") -> Dict[str, Any]:
    """Execute Enum4linux Windows/Samba enumeration tool."""
    if not _kali_client: return {"error": "Kali Client not initialized"}
    data = {"target": target, "additional_args": additional_args}
    return _kali_client.safe_post("api/tools/enum4linux", data)

@mcp.tool()
def server_health() -> Dict[str, Any]:
    """Check the health status of the Kali API server."""
    if not _kali_client: return {"error": "Kali Client not initialized"}
    return _kali_client.check_health()

@mcp.tool(name="execute_command")
def execute_command(command: str) -> Dict[str, Any]:
    """Execute an arbitrary command on the Kali server."""
    if not _kali_client: return {"error": "Kali Client not initialized"}
    return _kali_client.execute_command(command)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the Kali MCP Client")
    parser.add_argument("--server", type=str, default=DEFAULT_KALI_SERVER, 
                      help=f"Kali API server URL (default: {DEFAULT_KALI_SERVER})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_REQUEST_TIMEOUT,
                      help=f"Request timeout in seconds (default: {DEFAULT_REQUEST_TIMEOUT})")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()

def main():
    """Main entry point for the MCP server."""
    global _kali_client
    args = parse_args()
    
    # Configure logging based on debug flag
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Initialize the Kali Tools client
    _kali_client = KaliToolsClient(args.server, args.timeout)
    
    # Check server health and log the result
    health = _kali_client.check_health()
    if "error" in health:
        logger.warning(f"Unable to connect to Kali API server at {args.server}: {health['error']}")
        logger.warning("MCP server will start, but tool execution may fail")
    else:
        logger.info(f"Successfully connected to Kali API server at {args.server}")
        logger.info(f"Server health status: {health['status']}")
    
    logger.info("Starting Kali MCP server")
    mcp.run()

if __name__ == "__main__":
    main()
