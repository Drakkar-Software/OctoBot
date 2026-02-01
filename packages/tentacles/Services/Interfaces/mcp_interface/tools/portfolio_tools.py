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


def get_portfolio_tools_list() -> list:
    """Get list of portfolio tool definitions."""
    return [
        {
            "name": "get_portfolio",
            "description": "Get current portfolio holdings across all exchanges",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_balance",
            "description": "Get balance for a specific currency",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "currency": {
                        "type": "string",
                        "description": "Currency symbol (e.g., BTC, ETH, USDT)"
                    }
                },
                "required": ["currency"]
            }
        },
        {
            "name": "get_portfolio_value",
            "description": "Get total portfolio value",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    ]


async def execute_portfolio_tool(name: str, arguments: dict) -> dict:
    """Execute a portfolio tool."""
    if name == "get_portfolio":
        return await _get_portfolio()
    elif name == "get_balance":
        currency = arguments.get("currency")
        if not currency:
            return {"error": "currency parameter is required"}
        return await _get_balance(currency)
    elif name == "get_portfolio_value":
        return await _get_portfolio_value()
    else:
        return {"error": f"Unknown portfolio tool: {name}"}


async def _get_portfolio() -> dict:
    """Get full portfolio holdings."""
    try:
        exchange_managers = interfaces.AbstractInterface.get_exchange_managers()
        real_portfolio = {}
        simulated_portfolio = {}
        
        for exchange_manager in exchange_managers:
            if trading_api.is_trader_existing_and_enabled(exchange_manager):
                holdings_values = trading_api.get_current_holdings_values(exchange_manager)
                target_portfolio = simulated_portfolio if trading_api.is_trader_simulated(exchange_manager) else real_portfolio
                
                for currency, value in holdings_values.items():
                    target_portfolio[currency] = target_portfolio.get(currency, 0) + value
        
        return {
            "real": _format_portfolio(real_portfolio),
            "simulated": _format_portfolio(simulated_portfolio)
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_balance(currency: str) -> dict:
    """Get balance for specific currency."""
    try:
        exchange_managers = interfaces.AbstractInterface.get_exchange_managers()
        real_available = 0.0
        real_total = 0.0
        simulated_available = 0.0
        simulated_total = 0.0
        
        for exchange_manager in exchange_managers:
            if trading_api.is_trader_existing_and_enabled(exchange_manager):
                portfolio = trading_api.get_portfolio(exchange_manager)
                asset = portfolio.get(currency)
                
                if asset:
                    available = float(getattr(asset, 'available', 0))
                    total = float(getattr(asset, 'total', 0))
                    
                    if trading_api.is_trader_simulated(exchange_manager):
                        simulated_available += available
                        simulated_total += total
                    else:
                        real_available += available
                        real_total += total
        
        return {
            "currency": currency,
            "real": {
                "available": str(real_available),
                "total": str(real_total)
            },
            "simulated": {
                "available": str(simulated_available),
                "total": str(simulated_total)
            }
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_portfolio_value() -> dict:
    """Get total portfolio value."""
    try:
        exchange_managers = interfaces.AbstractInterface.get_exchange_managers()
        real_value = 0.0
        simulated_value = 0.0
        has_real = False
        has_simulated = False
        
        for exchange_manager in exchange_managers:
            if trading_api.is_trader_existing_and_enabled(exchange_manager):
                current_value = trading_api.get_current_portfolio_value(exchange_manager) or trading_api.get_origin_portfolio_value(exchange_manager)
                
                if trading_api.is_trader_simulated(exchange_manager):
                    simulated_value += current_value
                    has_simulated = True
                else:
                    real_value += current_value
                    has_real = True
        
        return {
            "has_real_trader": has_real,
            "has_simulated_trader": has_simulated,
            "real_value": real_value,
            "simulated_value": simulated_value,
            "total_value": real_value + simulated_value
        }
    except Exception as e:
        return {"error": str(e)}


def _format_portfolio(portfolio: dict) -> dict:
    """Format portfolio for JSON serialization."""
    return {currency: float(value) for currency, value in portfolio.items()}
