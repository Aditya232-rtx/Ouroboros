import asyncio
import logging
import os
import shutil
from typing import Dict, List, Optional
from dataclasses import dataclass
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import studio_client

logger = logging.getLogger(__name__)

@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: List[str]
    env: Dict[str, str] = None

class MCPManager:
    """
    Manages connections to Model Context Protocol (MCP) servers.
    """
    
    def __init__(self):
        self.servers: Dict[str, MCPServerConfig] = {}
        self.sessions: Dict[str, ClientSession] = {}
        self._setup_defaults()

    def _setup_defaults(self):
        """Configure default known servers"""
        # Ensure npx is available
        npx_path = shutil.which("npx")
        if not npx_path:
            logger.warning("npx not found. MCP servers may fail to start.")
            npx_path = "npx"

        env_base = os.environ.copy()
        
        # Filesystem Server (Default to /app/data or current dir)
        self.servers["filesystem"] = MCPServerConfig(
            name="filesystem",
            command=npx_path,
            args=["-y", "@modelcontextprotocol/server-filesystem", "/app/data"],
            env=env_base
        )

        # GitHub Server
        if os.getenv("GITHUB_TOKEN"):
             self.servers["github"] = MCPServerConfig(
                name="github",
                command=npx_path,
                args=["-y", "@modelcontextprotocol/server-github"],
                env=env_base # GITHUB_TOKEN should be in env
            )

        # GDrive Server
        # Requires client_id/secret usually, or specific auth flow.
        # Assuming env vars are present or instruction follows.
        self.servers["gdrive"] = MCPServerConfig(
            name="gdrive",
            command=npx_path,
            args=["-y", "@modelcontextprotocol/server-gdrive"],
            env=env_base
        )
        
        # Slack Server
        if os.getenv("SLACK_BOT_TOKEN"):
             self.servers["slack"] = MCPServerConfig(
                name="slack",
                command=npx_path,
                args=["-y", "@modelcontextprotocol/server-slack"],
                env=env_base
            )

    async def connect(self, server_name: str) -> Optional[ClientSession]:
        """
        Connect to a specific MCP server.
        Note: The mcp library's stdio_client is a context manager.
        Managing persistent sessions requires careful handling of the context.
        For now, this returns parameters to be used in a 'async with' block by the caller,
        OR we implement a managed connection.
        
        Refactoring to return params for now as keeping session open requires lifecycle management.
        """
        config = self.servers.get(server_name)
        if not config:
            logger.error(f"MCP server {server_name} not configured.")
            return None
            
        logger.info(f"Connecting to MCP server: {server_name}")
        
        params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env
        )
        
        return params

    def get_server_config(self, server_name: str) -> Optional[StdioServerParameters]:
         config = self.servers.get(server_name)
         if not config:
             return None
             
         return StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env
        )
