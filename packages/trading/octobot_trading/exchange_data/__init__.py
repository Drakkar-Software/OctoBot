#  Drakkar-Software OctoBot-Trading
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

from octobot_trading.exchange_data import funding
from octobot_trading.exchange_data.funding import (
    FundingUpdaterSimulator,
    FundingUpdater,
    FundingManager,
    FundingProducer,
    FundingChannel,
)
from octobot_trading.exchange_data import kline
from octobot_trading.exchange_data.kline import (
    KlineUpdaterSimulator,
    KlineProducer,
    KlineChannel,
    KlineManager,
    KlineUpdater,
)
from octobot_trading.exchange_data import markets
from octobot_trading.exchange_data.markets import (
    MarketsUpdaterSimulator,
    MarketsProducer,
    MarketsChannel,
    MarketsManager,
    MarketsUpdater,
)
from octobot_trading.exchange_data import ohlcv
from octobot_trading.exchange_data.ohlcv import (
    CandlesManager,
    PreloadedCandlesManager,
    get_symbol_close_candles,
    get_symbol_open_candles,
    get_symbol_high_candles,
    get_symbol_low_candles,
    get_symbol_volume_candles,
    get_symbol_time_candles,
    get_candle_as_list,
    OHLCVUpdaterSimulator,
    OHLCVProducer,
    OHLCVChannel,
    OHLCVUpdater,
)
from octobot_trading.exchange_data import order_book
from octobot_trading.exchange_data.order_book import (
    OrderBookUpdater,
    OrderBookProducer,
    OrderBookChannel,
    OrderBookTickerProducer,
    OrderBookTickerChannel,
    OrderBookManager,
    OrderBookUpdaterSimulator,
)
from octobot_trading.exchange_data import prices
from octobot_trading.exchange_data.prices import (
    MarkPriceUpdaterSimulator,
    MarkPriceProducer,
    MarkPriceChannel,
    PricesManager,
    calculate_mark_price_from_recent_trade_prices,
    MarkPriceUpdater,
    PriceEventsManager,
)
from octobot_trading.exchange_data import recent_trades
from octobot_trading.exchange_data.recent_trades import (
    RecentTradeProducer,
    RecentTradeChannel,
    LiquidationsProducer,
    LiquidationsChannel,
    RecentTradesManager,
    RecentTradeUpdater,
    RecentTradeUpdaterSimulator,
)
from octobot_trading.exchange_data import ticker
from octobot_trading.exchange_data.ticker import (
    TickerManager,
    TickerUpdater,
    TickerProducer,
    TickerChannel,
    MiniTickerProducer,
    MiniTickerChannel,
    TickerUpdaterSimulator,
)
from octobot_trading.exchange_data import contracts
from octobot_trading.exchange_data.contracts import (
    Contract,
    MarginContract,
    FutureContract,
    OptionContract,
    get_contract_type_from_symbol,
    update_contracts_from_positions,
    update_future_contract_from_dict,
    create_default_future_contract,
    create_default_option_contract,
    create_contract,
)
from octobot_trading.exchange_data import exchange_symbol_data
from octobot_trading.exchange_data.exchange_symbol_data import (
    ExchangeSymbolData,
)
from octobot_trading.exchange_data import exchange_symbols_data
from octobot_trading.exchange_data.exchange_symbols_data import (
    ExchangeSymbolsData,
)

import octobot_trading.constants as trading_constants
import octobot_backtesting.enums as backtesting_enums

UNAUTHENTICATED_UPDATER_PRODUCERS = [OHLCVUpdater, OrderBookUpdater, RecentTradeUpdater, TickerUpdater,
                                     KlineUpdater, MarkPriceUpdater, FundingUpdater, MarketsUpdater]
UNAUTHENTICATED_UPDATER_SIMULATOR_PRODUCERS = {
        trading_constants.OHLCV_CHANNEL: OHLCVUpdaterSimulator,
        trading_constants.ORDER_BOOK_CHANNEL: OrderBookUpdaterSimulator,
        trading_constants.RECENT_TRADES_CHANNEL: RecentTradeUpdaterSimulator,
        trading_constants.TICKER_CHANNEL: TickerUpdaterSimulator,
        trading_constants.KLINE_CHANNEL: KlineUpdaterSimulator,
        trading_constants.MARKETS_CHANNEL: MarketsUpdaterSimulator,
        trading_constants.MARK_PRICE_CHANNEL: MarkPriceUpdaterSimulator,
        trading_constants.FUNDING_CHANNEL: FundingUpdaterSimulator
    }

# Required data to run updater (requires at least one per list)
SIMULATOR_PRODUCERS_TO_POSSIBLE_DATA_TYPE = {
    trading_constants.OHLCV_CHANNEL: [backtesting_enums.ExchangeDataTables.OHLCV],
    trading_constants.ORDER_BOOK_CHANNEL: [backtesting_enums.ExchangeDataTables.ORDER_BOOK],
    trading_constants.RECENT_TRADES_CHANNEL: [backtesting_enums.ExchangeDataTables.RECENT_TRADES,
                                              backtesting_enums.ExchangeDataTables.OHLCV],
    trading_constants.TICKER_CHANNEL: [backtesting_enums.ExchangeDataTables.TICKER,
                                       backtesting_enums.ExchangeDataTables.OHLCV],
    trading_constants.KLINE_CHANNEL: [backtesting_enums.ExchangeDataTables.KLINE],
    # trading_constants.FUNDING_CHANNEL: [backtesting_enums.ExchangeDataTables.FUNDING] only hard coded value for now
}

# Required data to run real data updater (requires each per list)
SIMULATOR_PRODUCERS_TO_REAL_DATA_TYPE = {
    trading_constants.OHLCV_CHANNEL: [backtesting_enums.ExchangeDataTables.OHLCV],
    trading_constants.ORDER_BOOK_CHANNEL: [backtesting_enums.ExchangeDataTables.ORDER_BOOK],
    trading_constants.RECENT_TRADES_CHANNEL: [backtesting_enums.ExchangeDataTables.RECENT_TRADES],
    trading_constants.TICKER_CHANNEL: [backtesting_enums.ExchangeDataTables.TICKER],
    trading_constants.KLINE_CHANNEL: [backtesting_enums.ExchangeDataTables.KLINE],
    trading_constants.FUNDING_CHANNEL: [backtesting_enums.ExchangeDataTables.FUNDING],
}

__all__ = [
    "FundingUpdaterSimulator",
    "FundingUpdater",
    "FundingManager",
    "FundingProducer",
    "FundingChannel",
    "KlineUpdaterSimulator",
    "KlineProducer",
    "KlineChannel",
    "KlineManager",
    "KlineUpdater",
    "MarketsUpdaterSimulator",
    "MarketsProducer",
    "MarketsChannel",
    "MarketsManager",
    "MarketsUpdater",
    "CandlesManager",
    "PreloadedCandlesManager",
    "get_symbol_close_candles",
    "get_symbol_open_candles",
    "get_symbol_high_candles",
    "get_symbol_low_candles",
    "get_symbol_volume_candles",
    "get_symbol_time_candles",
    "get_candle_as_list",
    "OHLCVUpdaterSimulator",
    "OHLCVProducer",
    "OHLCVChannel",
    "OHLCVUpdater",
    "OrderBookUpdater",
    "OrderBookProducer",
    "OrderBookChannel",
    "OrderBookTickerProducer",
    "OrderBookTickerChannel",
    "OrderBookManager",
    "OrderBookUpdaterSimulator",
    "MarkPriceUpdaterSimulator",
    "MarkPriceProducer",
    "MarkPriceChannel",
    "PricesManager",
    "calculate_mark_price_from_recent_trade_prices",
    "MarkPriceUpdater",
    "PriceEventsManager",
    "RecentTradeProducer",
    "RecentTradeChannel",
    "LiquidationsProducer",
    "LiquidationsChannel",
    "RecentTradesManager",
    "RecentTradeUpdater",
    "RecentTradeUpdaterSimulator",
    "TickerManager",
    "TickerUpdater",
    "TickerProducer",
    "TickerChannel",
    "MiniTickerProducer",
    "MiniTickerChannel",
    "TickerUpdaterSimulator",
    "Contract",
    "MarginContract",
    "FutureContract",
    "OptionContract",
    "get_contract_type_from_symbol",
    "update_contracts_from_positions",
    "update_future_contract_from_dict",
    "create_default_future_contract",
    "create_default_option_contract",
    "create_contract",
    "ExchangeSymbolsData",
    "ExchangeSymbolData",
    "UNAUTHENTICATED_UPDATER_PRODUCERS",
    "UNAUTHENTICATED_UPDATER_SIMULATOR_PRODUCERS",
    "SIMULATOR_PRODUCERS_TO_POSSIBLE_DATA_TYPE",
    "SIMULATOR_PRODUCERS_TO_REAL_DATA_TYPE",
]
