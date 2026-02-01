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


def get_trading_tools_list() -> list:
    """Get list of trading tool definitions."""
    return [
        {
            "name": "get_trades_history",
            "description": "Get trade history, optionally filtered by symbol",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of trades to return",
                        "default": 50
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Optional symbol to filter trades (e.g., BTC/USDT)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_reference_market",
            "description": "Get reference market currency",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    ]


async def execute_trading_tool(name: str, arguments: dict) -> dict:
    """Execute a trading tool."""
    if name == "get_trades_history":
        limit = arguments.get("limit", 50)
        symbol = arguments.get("symbol")
        return await _get_trades_history(limit, symbol)
    elif name == "get_reference_market":
        return await _get_reference_market()
    else:
        return {"error": f"Unknown trading tool: {name}"}


async def _get_trades_history(limit: int = 50, symbol: str = None) -> dict:
    """Get trade history."""
    try:
        exchange_managers = interfaces.AbstractInterface.get_exchange_managers()
        real_trades = []
        simulated_trades = []
        
        for exchange_manager in exchange_managers:
            if trading_api.is_trader_existing_and_enabled(exchange_manager):
                is_simulated = trading_api.is_trader_simulated(exchange_manager)
                trades = trading_api.get_trade_history(
                    exchange_manager,
                    quote=None,
                    symbol=symbol,
                    since=None,
                    as_dict=True
                )
                
                if is_simulated:
                    simulated_trades.extend(trades)
                else:
                    real_trades.extend(trades)
        
        # Sort each list by timestamp (newest first)
        def get_timestamp(trade):
            if isinstance(trade, dict):
                return trade.get('timestamp', trade.get('executed_time', 0))
            return getattr(trade, 'timestamp', getattr(trade, 'executed_time', 0))
        
        real_trades.sort(key=get_timestamp, reverse=True)
        simulated_trades.sort(key=get_timestamp, reverse=True)
        
        # Limit each list
        real_trades = real_trades[:limit]
        simulated_trades = simulated_trades[:limit]
        
        return {
            "real": real_trades,
            "simulated": simulated_trades,
            "count": len(real_trades) + len(simulated_trades)
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_reference_market() -> dict:
    """Get reference market currency."""
    try:
        reference_market = trading_api.get_reference_market(
            interfaces.AbstractInterface.bot_api.get_global_config()
        )
        return {
            "reference_market": reference_market
        }
    except Exception as e:
        return {"error": str(e)}
