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
import json

from .portfolio_tools import (
    get_portfolio_tools_list,
    execute_portfolio_tool
)
from .order_tools import (
    get_order_tools_list,
    execute_order_tool
)
from .trading import (
    get_trading_tools_list,
    execute_trading_tool
)
from .exchange_data_tools import (
    get_exchange_data_tools_list,
    execute_exchange_data_tool
)


def register_tools(server):
    """Register all MCP tools with the server."""
    # Collect all tools
    all_tools = []
    all_tools.extend(get_portfolio_tools_list())
    all_tools.extend(get_order_tools_list())
    all_tools.extend(get_trading_tools_list())
    all_tools.extend(get_exchange_data_tools_list())
    
    # Register single list_tools handler
    @server.list_tools()
    async def handle_list_tools() -> list:
        """List all available MCP tools."""
        return all_tools
    
    # Register single call_tool handler
    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict) -> list:
        """Handle tool calls and route to appropriate handler."""
        try:
            # Try portfolio tools
            if name in [tool["name"] for tool in get_portfolio_tools_list()]:
                result = await execute_portfolio_tool(name, arguments)
                return [{"content": [{"type": "text", "text": json.dumps(result)}]}]
            
            # Try order tools
            if name in [tool["name"] for tool in get_order_tools_list()]:
                result = await execute_order_tool(name, arguments)
                return [{"content": [{"type": "text", "text": json.dumps(result)}]}]
            
            # Try trading tools
            if name in [tool["name"] for tool in get_trading_tools_list()]:
                result = await execute_trading_tool(name, arguments)
                return [{"content": [{"type": "text", "text": json.dumps(result)}]}]
            
            # Try exchange data tools
            if name in [tool["name"] for tool in get_exchange_data_tools_list()]:
                result = await execute_exchange_data_tool(name, arguments)
                return [{"content": [{"type": "text", "text": json.dumps(result)}]}]
            
            return [{"error": f"Unknown tool: {name}"}]
        except Exception as e:
            return [{"error": str(e)}]
