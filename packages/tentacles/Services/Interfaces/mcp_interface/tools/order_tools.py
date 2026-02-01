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
import octobot_trading.api as trading_api
import octobot_services.interfaces as interfaces


def get_order_tools_list() -> list:
    """Get list of order tool definitions."""
    return [
        {
            "name": "get_open_orders",
            "description": "Get open orders, optionally filtered by exchange or symbol",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "exchange_id": {
                        "type": "string",
                        "description": "Optional exchange ID to filter orders"
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Optional symbol to filter orders (e.g., BTC/USDT)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_order_details",
            "description": "Get details for a specific order by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID"
                    }
                },
                "required": ["order_id"]
            }
        }
    ]


async def execute_order_tool(name: str, arguments: dict) -> dict:
    """Execute an order tool."""
    if name == "get_open_orders":
        exchange_id = arguments.get("exchange_id")
        symbol = arguments.get("symbol")
        return await _get_open_orders(exchange_id, symbol)
    elif name == "get_order_details":
        order_id = arguments.get("order_id")
        if not order_id:
            return {"error": "order_id parameter is required"}
        return await _get_order_details(order_id)
    else:
        return {"error": f"Unknown order tool: {name}"}


async def _get_open_orders(exchange_id: str = None, symbol: str = None) -> dict:
    """Get open orders."""
    try:
        exchange_managers = interfaces.AbstractInterface.get_exchange_managers()
        real_orders = []
        simulated_orders = []
        
        for exchange_manager in exchange_managers:
            if trading_api.is_trader_existing_and_enabled(exchange_manager):
                is_simulated = trading_api.is_trader_simulated(exchange_manager)
                manager_id = trading_api.get_exchange_manager_id(exchange_manager)
                
                # Filter by exchange_id if provided
                if exchange_id and manager_id != exchange_id:
                    continue
                
                orders = trading_api.get_open_orders(exchange_manager)
                
                # Filter by symbol if provided
                if symbol:
                    orders = [o for o in orders if o.symbol == symbol]
                
                if is_simulated:
                    simulated_orders.extend(orders)
                else:
                    real_orders.extend(orders)
        
        return {
            "real": [_format_order(order) for order in real_orders],
            "simulated": [_format_order(order) for order in simulated_orders]
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_order_details(order_id: str) -> dict:
    """Get specific order details."""
    try:
        exchange_managers = interfaces.AbstractInterface.get_exchange_managers()
        all_orders = []
        
        for exchange_manager in exchange_managers:
            if trading_api.is_trader_existing_and_enabled(exchange_manager):
                # Get open orders
                all_orders.extend(trading_api.get_open_orders(exchange_manager))
                # Get all orders (including historical)
                all_orders.extend(trading_api.get_all_orders(exchange_manager))
        
        # Find order by ID
        for order in all_orders:
            if order.order_id == order_id or getattr(order, 'exchange_order_id', None) == order_id:
                return _format_order(order)
        
        return {"error": f"Order {order_id} not found"}
    except Exception as e:
        return {"error": str(e)}


def _format_order(order) -> dict:
    """Format order for JSON serialization."""
    try:
        return {
            "order_id": order.order_id,
            "exchange_order_id": getattr(order, 'exchange_order_id', None),
            "symbol": order.symbol,
            "side": order.side.value if hasattr(order.side, 'value') else str(order.side),
            "order_type": order.order_type.value if hasattr(order.order_type, 'value') else str(order.order_type),
            "status": order.status.value if hasattr(order.status, 'value') else str(order.status),
            "price": float(order.price) if order.price else None,
            "amount": float(order.amount) if order.amount else None,
            "filled": float(order.filled) if hasattr(order, 'filled') and order.filled else None,
            "creation_time": float(order.creation_time) if hasattr(order, 'creation_time') else None,
            "exchange": trading_api.get_order_exchange_name(order)
        }
    except Exception as e:
        return {"error": f"Error formatting order: {str(e)}"}
