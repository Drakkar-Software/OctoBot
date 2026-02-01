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
import os
import asyncio

import octobot_services.constants as services_constants
import octobot_services.interfaces as interfaces

from .mcp_server import MCPServer


class MCPInterface(interfaces.AbstractInterface):
    REQUIRED_SERVICES = False

    def __init__(self, config):
        super().__init__(config)
        self.logger = self.get_logger()
        self.mcp_server = None
        self.mcp_address = None
        self.mcp_port = None
        self._server_task = None

    def _init_mcp_settings(self):
        """Initialize MCP server settings from config with environment variable overrides."""
        try:
            self.mcp_address = os.getenv(
                services_constants.ENV_MCP_ADDRESS,
                self.config[services_constants.CONFIG_CATEGORY_SERVICES]
                [services_constants.CONFIG_MCP][services_constants.CONFIG_MCP_IP]
            )
        except KeyError:
            self.mcp_address = os.getenv(
                services_constants.ENV_MCP_ADDRESS,
                services_constants.DEFAULT_MCP_IP
            )
        
        try:
            self.mcp_port = int(os.getenv(
                services_constants.ENV_MCP_PORT,
                self.config[services_constants.CONFIG_CATEGORY_SERVICES]
                [services_constants.CONFIG_MCP][services_constants.CONFIG_MCP_PORT]
            ))
        except KeyError:
            self.mcp_port = int(os.getenv(
                services_constants.ENV_MCP_PORT,
                services_constants.DEFAULT_MCP_PORT
            ))

    async def _inner_start(self) -> bool:
        """Start MCP server with HTTP transport."""
        self._init_mcp_settings()
        
        self.mcp_server = MCPServer()
        
        # Start HTTP server
        self.logger.info(f"Starting MCP server with HTTP transport (address: {self.mcp_address}, port: {self.mcp_port})")
        try:
            self._server_task = asyncio.create_task(self.mcp_server.start_http(self.mcp_address, self.mcp_port))
        except NotImplementedError as e:
            self.logger.error(f"Failed to start HTTP transport: {e}")
            return False
        
        return True

    async def stop(self):
        """Stop MCP server."""
        if self.mcp_server:
            await self.mcp_server.stop()
        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
        self.logger.info("MCP interface stopped")

    def get_connection_info(self):
        """Return connection info for LLMService (HTTP URL)."""
        return {
            "transport": "http",
            "url": f"http://{self.mcp_address}:{self.mcp_port}",
            "name": "octobot-internal"
        }
