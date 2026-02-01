#  Drakkar-Software OctoBot-Interfaces
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import logging

MCP_AVAILABLE = False
try:
    from mcp.server import Server
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from .tools import register_tools


class MCPServer:
    """MCP server implementation for OctoBot trading tools."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.server = None
        self._running = False
        
    async def _create_server(self):
        """Create and configure MCP server with tools."""
        if not MCP_AVAILABLE:
            raise ImportError(
                "MCP Python SDK not available. Install with: pip install mcp"
            )
        
        self.server = Server("octobot-mcp")
        register_tools(self.server)
        return self.server
    
    async def start_http(self, host: str, port: int):
        """Start MCP server with HTTP transport.
        
        Note: HTTP transport implementation depends on MCP SDK version.
        This is a placeholder that will be implemented when HTTP transport
        is stable in the MCP SDK.
        """
        if not MCP_AVAILABLE:
            self.logger.error("MCP Python SDK not available")
            return
        
        self.logger.warning(
            f"HTTP transport requested for {host}:{port}, "
            "but HTTP server transport is not yet fully implemented. "
            "HTTP support will be added when MCP SDK HTTP transport is stable."
        )
        
        # TODO: Implement HTTP transport when MCP SDK provides stable HTTP server API
        # For now, raise an error to indicate HTTP is not yet supported
        raise NotImplementedError(
            "HTTP transport is not yet implemented."
        )
    
    async def stop(self):
        """Stop MCP server."""
        self._running = False
        if self.server:
            # Server cleanup if needed
            pass
