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
import octobot_trading.enums as enums
import octobot_services.interfaces as interfaces


def get_exchange_data_tools_list() -> list:
    """Get list of exchange data tool definitions."""
    return [
        {
            "name": "get_current_price",
            "description": "Get the current price of a trading symbol",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Trading symbol (e.g., BTC/USDT)"
                    },
                    "exchange_id": {
                        "type": "string",
                        "description": "Optional specific exchange ID to query"
                    }
                },
                "required": ["symbol"]
            }
        }
    ]


async def execute_exchange_data_tool(name: str, arguments: dict) -> dict:
    """Execute an exchange data tool."""
    if name == "get_current_price":
        symbol = arguments.get("symbol")
        if not symbol:
            return {"error": "symbol parameter is required"}
        exchange_id = arguments.get("exchange_id")
        return await _get_current_price(symbol, exchange_id)
    else:
        return {"error": f"Unknown exchange data tool: {name}"}


async def _get_current_price(symbol: str, exchange_id: str = None) -> dict:
    """Get current price for a symbol."""
    try:
        exchange_managers = interfaces.AbstractInterface.get_exchange_managers()
        prices = {}
        
        for exchange_manager in exchange_managers:
            if trading_api.is_trader_existing_and_enabled(exchange_manager):
                manager_id = trading_api.get_exchange_manager_id(exchange_manager)
                
                # Filter by exchange_id if provided
                if exchange_id and manager_id != exchange_id:
                    continue
                
                try:
                    ticker = await exchange_manager.exchange.get_price_ticker(symbol)
                    if ticker:
                        close_price = ticker.get(enums.ExchangeConstantsTickersColumns.CLOSE.value)
                        if close_price is not None:
                            prices[manager_id] = float(close_price)
                except Exception as e:
                    # Skip this exchange if ticker fetch fails
                    # (symbol might not exist on this exchange, or exchange doesn't support ticker)
                    continue
        
        if not prices:
            return {
                "symbol": symbol,
                "error": "No price data available for this symbol on any enabled exchange"
            }
        
        return {
            "symbol": symbol,
            "prices": prices,
            "count": len(prices)
        }
    except Exception as e:
        return {"error": str(e)}
