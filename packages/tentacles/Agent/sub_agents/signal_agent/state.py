#  Drakkar-Software OctoBot-Tentacles
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

"""
AI Agent State definitions for the trading mode agents.
"""
from typing import Dict, List, Optional, Any
from typing_extensions import Annotated, TypedDict


def merge_dicts(a: dict, b: dict) -> dict:
    """Merge two dictionaries, with b overwriting a."""
    return {**a, **b}


def replace_value(a: Any, b: Any) -> Any:
    """Replace value a with value b."""
    return b


class PortfolioState(TypedDict, total=False):
    """Current portfolio state from trading API."""
    holdings: Dict[str, float]  # {asset: amount}
    holdings_value: Dict[str, float]  # {asset: value_in_reference_market}
    total_value: float
    reference_market: str
    available_balance: float


class OrdersState(TypedDict, total=False):
    """Current orders state from trading API."""
    open_orders: List[Dict[str, Any]]
    pending_orders: List[Dict[str, Any]]
    recent_trades: List[Dict[str, Any]]


class StrategyData(TypedDict, total=False):
    """Strategy evaluation data."""
    eval_note: float
    description: str
    metadata: Dict[str, Any]
    cryptocurrency: Optional[str]
    symbol: Optional[str]
    evaluation_type: str


class AIAgentState(TypedDict, total=False):
    """
    Shared state for all AI trading agents.
    Contains strategy data, portfolio info, and agent outputs.
    """
    # Input data
    global_strategy_data: Dict[str, List[Any]]
    crypto_strategy_data: Dict[str, Dict[str, List[Any]]]  # {cryptocurrency: strategy_data}
    cryptocurrencies: List[str]
    reference_market: str
    
    # Trading context
    portfolio: Dict[str, Any]
    orders: Dict[str, Any]
    current_distribution: Dict[str, float]  # Current portfolio distribution percentages
    
    # Agent outputs
    signal_outputs: Dict[str, Any]
    risk_output: Optional[Any]
    signal_synthesis: Optional[Any]
    distribution_output: Optional[Any]
    
    # Metadata
    exchange_name: str
    timestamp: str
