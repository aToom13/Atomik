"""
MCP Client Manager - Python 3.13 Compatible
Works around asyncio/anyio issues in MCP SDK 1.24.0
"""
import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Any
import sys

# MCP SDK imports
try:
    from mcp import ClientSession
    MCP_SDK_AVAILABLE = True
except ImportError:
    MCP_SDK_AVAILABLE = False
    print("⚠️ MCP SDK not installed. Run: pip install mcp")


class MCPProcess:
    """Manages a single MCP server process with manual stdio handling"""
    
    def __init__(self, name: str, command: str, args: list, env: dict = None):
        self.name = name
        self.command = command
        self.args = args
        self.env = env
        self.process = None
        self.session = None
        self.lock = asyncio.Lock()
        
    async def start(self, timeout: float = 30.0) -> bool:
        """Start the MCP server process"""
        try:
            # Prepare environment
            full_env = os.environ.copy()
            if self.env:
                full_env.update(self.env)
            
            # Start subprocess
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=full_env
            )
            
            # Wait a moment for server to be ready
            await asyncio.sleep(1.0)
            
            # Check if process started successfully
            if self.process.returncode is not None:
                stderr = await self.process.stderr.read()
                raise RuntimeError(f"Process failed: {stderr.decode()}")
            
            print(f"✅ MCP: Connected to '{self.name}'")
            
            # Start a background task to read stderr for debugging
            async def read_stderr():
                if self.process and self.process.stderr:
                    while True:
                        try:
                            line = await self.process.stderr.readline()
                            if not line: break
                            print(f"🔴 [{self.name}] stderr: {line.decode().strip()}")
                        except:
                            break
            
            asyncio.create_task(read_stderr())
            
            # === PERFORM MCP HANDSHAKE ===
            try:
                # 1. Send Initialize
                init_request = {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "AtomikClient", "version": "1.0"}
                    }
                }
                self.process.stdin.write((json.dumps(init_request) + "\n").encode())
                await self.process.stdin.drain()
                
                # 2. Receive Initialized Response
                line = await asyncio.wait_for(self.process.stdout.readline(), timeout=5.0)
                json.loads(line.decode()) # Validate but ignore details
                
                # 3. Send Initialized Notification
                notify = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {}
                }
                self.process.stdin.write((json.dumps(notify) + "\n").encode())
                await self.process.stdin.drain()
                
            except Exception as e:
                print(f"❌ MCP Handshake failed for '{self.name}': {e}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ MCP: Failed to start '{self.name}': {e}")
            if self.process and self.process.returncode is None:
                try:
                    self.process.kill()
                    await self.process.wait()
                except:
                    pass
            return False
    
    async def call_tool(self, tool_name: str, args: dict = None) -> dict:
        """Call a tool via JSON-RPC"""
        if not self.process or self.process.returncode is not None:
            raise RuntimeError(f"Process not running for {self.name}")
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args or {}
            }
        }
        
        async with self.lock:
            # Send request
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()
            
            # Read response (with timeout)
            try:
                import time
                start_time = time.time()
                print(f"⏳ Tool call '{tool_name}' waiting for response (max 1200s)...", flush=True)
                
                # Using 1200 seconds explicitly
                line = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=1200.0 
                )
                
                duration = time.time() - start_time
                print(f"✅ Tool call '{tool_name}' received response in {duration:.2f}s.", flush=True)
                return json.loads(line.decode())
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                print(f"❌ Tool call '{tool_name}' TIMED OUT after {duration:.2f}s (Limit: 1200s). Check intermediate timeouts!", flush=True)
                raise RuntimeError(f"Tool call timed out: {tool_name}")
            except Exception as e:
                 print(f"❌ Tool call '{tool_name}' FAILED with error: {e}", flush=True)
                 raise


    async def list_tools(self) -> list:
        """List available tools via JSON-RPC"""
        if not self.process or self.process.returncode is not None:
            return []
            
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        try:
            async with self.lock:
                # Send request
                request_json = json.dumps(request) + "\n"
                self.process.stdin.write(request_json.encode())
                await self.process.stdin.drain()
                
                # Read response
                line = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=5.0
                )
            
            response = json.loads(line.decode())
            if "result" in response and "tools" in response["result"]:
                return response["result"]["tools"]
            return []
        except Exception as e:
            print(f"❌ MCP: Failed to list tools from '{self.name}': {e}")
            return []
    
    async def stop(self):
        """Stop the MCP server process"""
        if self.process and self.process.returncode is None:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            except:
                pass


class MCPClientManager:
    """Manages connections to external MCP servers - Python 3.13 compatible"""
    
    def __init__(self, config_path: str = None):
        self.processes = {}  # server_name -> MCPProcess
        self.bridge_processes = {}  # server_name -> subprocess.Popen (for bridges)
        self._config_path = config_path
        self._background_tasks = set()
    
    @property
    def config_path(self) -> Path:
        if self._config_path:
            return Path(self._config_path)
        return Path(__file__).parent / "servers.json"
    
    @property
    def connected_servers(self) -> list:
        return list(self.processes.keys())
    
    async def connect(self, name: str, command: str, args: list, env: dict = None) -> bool:
        """Connect to a single MCP server"""
        if not MCP_SDK_AVAILABLE:
            print(f"❌ MCP SDK not available, cannot connect to {name}")
            return False
        
        process = MCPProcess(name, command, args, env)
        success = await process.start()
        
        if success:
            self.processes[name] = process
        
        return success
    
    async def connect_from_config(self) -> int:
        """Load and connect to all servers defined in config file"""
        if not self.config_path.exists():
            print(f"⚠️ MCP config not found: {self.config_path}")
            return 0
        
        try:
            config = json.loads(self.config_path.read_text())
        except json.JSONDecodeError as e:
            print(f"❌ MCP config parse error: {e}")
            return 0
        
        servers = config.get("mcpServers", {})
        if not servers:
            print("ℹ️ No MCP servers configured")
            return 0
        
        # First, start any required bridges
        for name, server in servers.items():
            bridge_config = server.get("bridge")
            if bridge_config:
                await self._start_bridge(name, bridge_config)
        
        # Connect to all servers concurrently
        tasks = []
        for name, server in servers.items():
            command = server.get("command")
            args = server.get("args", [])
            env = server.get("env", {})
            
            if not command:
                print(f"⚠️ MCP: Server '{name}' missing command")
                continue
            
            tasks.append(self.connect(name, command, args, env))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r is True)
        
        return success_count
    
    async def _start_bridge(self, name: str, bridge_config: dict):
        """Start a bridge process for a server (e.g., WhatsApp bridge)"""
        command = bridge_config.get("command")
        cwd = bridge_config.get("cwd")
        
        if not command:
            return
        
        # Check if bridge is already running
        if name in self.bridge_processes:
            proc = self.bridge_processes[name]
            if proc.poll() is None:  # Still running
                print(f"ℹ️ Bridge for '{name}' already running")
                return
        
        try:
            print(f"🚀 Starting bridge for '{name}'...")
            proc = subprocess.Popen(
                [command],
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True  # Detach from parent
            )
            self.bridge_processes[name] = proc
            
            # Wait for bridge to be ready
            await asyncio.sleep(3.0)
            
            if proc.poll() is None:
                print(f"✅ Bridge for '{name}' started (PID: {proc.pid})")
            else:
                stderr = proc.stderr.read().decode() if proc.stderr else ""
                print(f"❌ Bridge for '{name}' failed: {stderr[:200]}")
        except Exception as e:
            print(f"❌ Failed to start bridge for '{name}': {e}")
    
    async def list_tools(self, server: str = None) -> list:
        """List available tools from connected servers"""
        tools = []
        targets = [server] if server else self.processes.keys()
        
        for name in targets:
            if name not in self.processes:
                continue
            
            # Fetch tools dynamically
            server_tools = await self.processes[name].list_tools()
            for tool in server_tools:
                tool["server"] = name
                tools.append(tool)
        
        return tools
    
    async def call_tool(self, server: str, tool_name: str, args: dict = None) -> str:
        """Call a tool on a connected MCP server"""
        if server not in self.processes:
            return f"Error: Server '{server}' not connected"
        
        try:
            result = await self.processes[server].call_tool(tool_name, args)
            
            # Extract result from JSON-RPC response
            if "result" in result:
                content = result["result"].get("content", [])
                if content and isinstance(content, list):
                    texts = [item.get("text", "") for item in content if "text" in item]
                    return "\n".join(texts) if texts else str(result["result"])
                return str(result["result"])
            elif "error" in result:
                return f"Error: {result['error']}"
            
            return str(result)
            
        except Exception as e:
            return f"Error calling {server}:{tool_name}: {e}"
    
    async def disconnect(self, server: str):
        """Disconnect from a specific server"""
        if server in self.processes:
            await self.processes[server].stop()
            del self.processes[server]
    
    async def disconnect_all(self):
        """Disconnect from all servers and stop bridges"""
        tasks = [self.disconnect(name) for name in list(self.processes.keys())]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Stop all bridge processes
        for name, proc in list(self.bridge_processes.items()):
            try:
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=5)
                    print(f"🛑 Bridge for '{name}' stopped")
            except Exception as e:
                try:
                    proc.kill()
                except:
                    pass
        self.bridge_processes.clear()
        
        print("ℹ️ MCP: Disconnected from all servers")
    
    def get_gemini_declarations(self) -> list:
        """
        Generate Gemini function declarations from connected MCP servers.
        Call this AFTER connect_from_config() to get dynamic declarations.
        """
        declarations = []
        
        for server_name in self.processes.keys():
            # Get tools for this server
            tools = self._get_server_tools(server_name)
            
            for tool in tools:
                # Convert to Gemini format with mcp_ prefix
                decl = {
                    "name": f"mcp_{server_name.replace('-', '_')}_{tool['name']}",
                    "description": f"[MCP:{server_name}] {tool.get('description', tool['name'])}",
                    "parameters": self._convert_schema(tool.get('inputSchema', {}))
                }
                declarations.append(decl)
        
        return declarations
    
    def _get_server_tools(self, server_name: str) -> list:
        """Get tool definitions for a server (from config or defaults)"""
        # Read from config for custom tool definitions
        if self.config_path.exists():
            try:
                config = json.loads(self.config_path.read_text())
                server_config = config.get("mcpServers", {}).get(server_name, {})
                if "tools" in server_config:
                    return server_config["tools"]
            except:
                pass
        
        # Default tool definitions for known servers (actual MCP tool names)
        defaults = {
            "memory": [
                # Knowledge graph memory server tools
                {"name": "create_entities", "description": "Yeni entities oluştur (isim, tip, observations)", "inputSchema": {"type": "object", "properties": {"entities": {"type": "array", "description": "Entity listesi [{name, entityType, observations}]"}}, "required": ["entities"]}},
                {"name": "search_nodes", "description": "Knowledge graph'ta arama yap", "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "description": "Arama sorgusu"}}, "required": ["query"]}},
                {"name": "open_nodes", "description": "Belirli entity'leri getir", "inputSchema": {"type": "object", "properties": {"names": {"type": "array", "description": "Entity isimleri listesi"}}, "required": ["names"]}}
            ],
            "sequential-thinking": [
                # Sequential thinking requires thought, thoughtNumber, totalThoughts, nextThoughtNeeded
                {"name": "sequentialthinking", "description": "Karmaşık problemleri çözmek için dinamik düşünme. Uyarı: totalThoughts dinamik olmalı, sabit 4 değil.", "inputSchema": {"type": "object", "properties": {"thought": {"type": "string"}, "thoughtNumber": {"type": "integer"}, "totalThoughts": {"type": "integer"}, "nextThoughtNeeded": {"type": "boolean"}}, "required": ["thought", "thoughtNumber", "totalThoughts", "nextThoughtNeeded"]}}
            ]
        }
        
        return defaults.get(server_name, [])
    
    def _convert_schema(self, schema: dict) -> dict:
        """Convert JSON Schema to Gemini parameter format"""
        if not schema:
            return {"type": "OBJECT", "properties": {}}
        
        result = {"type": "OBJECT", "properties": {}}
        
        for prop, details in schema.get("properties", {}).items():
            prop_type = details.get("type", "string").upper()
            result["properties"][prop] = {
                "type": prop_type,
                "description": details.get("description", prop)
            }
        
        if "required" in schema:
            result["required"] = schema["required"]
        
        return result
    
    def execute_tool_sync(self, tool_name: str, args: dict) -> str:
        """
        Execute an MCP tool synchronously.
        tool_name format: mcp_servername_toolname (e.g., mcp_memory_store_memory)
        """
        import concurrent.futures
        
        # Parse tool name: mcp_servername_toolname -> server, tool
        if not tool_name.startswith("mcp_"):
            return f"❌ Not an MCP tool: {tool_name}"
        
        rest = tool_name[4:]  # Remove 'mcp_' prefix
        
        # Find matching server by checking connected servers
        # Server names have dashes replaced with underscores in tool names
        matched_server = None
        actual_tool = None
        
        for server in self.processes.keys():
            # Convert server name to underscore format for matching
            server_prefix = server.replace("-", "_") + "_"
            if rest.startswith(server_prefix):
                matched_server = server
                actual_tool = rest[len(server_prefix):]
                break
        
        if not matched_server:
            return f"❌ No matching MCP server for tool: {tool_name}"
        
        # Execute async call safely from sync context
        try:
            process = self.processes[matched_server]
            
            # Find the loop where the process was created
            # Usually strict asyncio processes are bound to the loop they were created in
            # We need to schedule the coroutine in THAT loop
            
            loop = None
            if hasattr(process, 'process') and process.process and hasattr(process.process, '_loop'):
                 loop = process.process._loop
            
            if loop is None:
                # Fallback to getting running loop or creating new one if none exists
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            
            # Check if we are in the same loop
            current_loop = None
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                pass
            
            if loop.is_running() and current_loop == loop:
                 # We are inside the loop, but this is a sync function? 
                 # This implies we are blocking the loop. This is dangerous.
                 # But if specific to Gemini tool execution, it might be in a thread pool.
                 import concurrent.futures
                 f = concurrent.futures.Future()
                 asyncio.create_task(self._wrap_future(f, process.call_tool(actual_tool, args)))
                 return f.result(timeout=30)
            
            # Schedule in the loop
            future = asyncio.run_coroutine_threadsafe(
                process.call_tool(actual_tool, args),
                loop
            )
            
            try:
                import time
                start_time = time.time()
                print(f"🔄 MCP future.result() waiting (max 1200s)...", flush=True)
                result = future.result(timeout=1200)
                duration = time.time() - start_time
                print(f"✅ MCP future completed in {duration:.2f}s", flush=True)
                
                # Parse result
                if isinstance(result, dict):
                    if "result" in result:
                        content = result["result"].get("content", [])
                        if content and isinstance(content, list):
                            texts = [item.get("text", "") for item in content if "text" in item]
                            return "\n".join(texts) if texts else str(result["result"])
                        return str(result["result"])
                    elif "error" in result:
                        return f"MCP error {result['error'].get('code', '')}: {result['error'].get('message', '')}"
                
                return str(result) if result else "✅ OK"
                
            except concurrent.futures.TimeoutError:
                duration = time.time() - start_time
                print(f"❌ MCP future TIMED OUT after {duration:.2f}s (Limit: 1200s)", flush=True)
                return f"❌ MCP call timed out: {actual_tool}"
                 
        except Exception as e:
            return f"❌ MCP error: {e}"

    async def _wrap_future(self, future, coro):
        try:
            result = await coro
            future.set_result(result)
        except Exception as e:
            future.set_exception(e)


# Global singleton
_manager: Optional[MCPClientManager] = None


def get_mcp_manager() -> MCPClientManager:
    """Get or create the global MCP client manager"""
    global _manager
    if _manager is None:
        _manager = MCPClientManager()
    return _manager


def get_mcp_declarations() -> list:
    """
    Get Gemini tool declarations for all connected MCP servers.
    Call after MCP initialization.
    """
    manager = get_mcp_manager()
    return manager.get_gemini_declarations()


def execute_mcp_tool(name: str, args: dict) -> str:
    """
    Execute an MCP tool by name.
    Used by tools/executor.py as a single entry point.
    """
    manager = get_mcp_manager()
    return manager.execute_tool_sync(name, args)