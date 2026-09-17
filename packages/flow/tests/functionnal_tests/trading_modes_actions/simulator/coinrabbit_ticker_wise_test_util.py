"""
CoinRabbit ticker-wise symbol functional test helpers.

Portfolio keys: reference USDT@ETH; after index rebalance on CoinRabbit, BTC@BTC is acquired
(CoinRabbit lists BTC@BTC/USDT@<network> only — no ETH@ETH/USDT@ETH market; index still
configures ETH@ETH in the basket alongside BTC@BTC).
"""
import contextlib
import decimal
import time
import typing

import mock

import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.enums as common_enums
import octobot_commons.constants as commons_constants
import octobot_commons.symbols as commons_symbols
import octobot_commons.tests.test_config as test_config
import octobot_trading.api as trading_api
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.exchanges.util.exchange_data as exchange_data
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools
import octobot_flow.repositories.exchange as exchange_repositories

EXCHANGE_INTERNAL_NAME = "coinrabbit"
REFERENCE_ASSET = "USDT@ETH"
INDEX_COINS = ("ETH@ETH", "BTC@BTC")
# CoinRabbit exposes BTC@BTC/USDT@<network> pairs only (no ETH@ETH/USDT@ETH).
REQUIRED_MARKET_SYMBOLS = ("BTC@BTC/USDT@ETH",)
TRADED_PAIR = "BTC@BTC/USDT@ETH"
# USDT@ETH may be omitted from the dump when fully allocated to the index leg.
EXPECTED_PORTFOLIO_KEYS_AFTER_REBALANCE = ("BTC@BTC",)

INITIAL_REFERENCE_HOLDING = 1000.0
MOCK_CLOSE_BY_SYMBOL: dict[str, float] = {
    "BTC@BTC/USDT@ETH": 100_000.0,
}


@contextlib.asynccontextmanager
async def coinrabbit_exchange_manager_context():
    config = test_config.load_test_config()
    if EXCHANGE_INTERNAL_NAME not in config[commons_constants.CONFIG_EXCHANGES]:
        config[commons_constants.CONFIG_EXCHANGES][EXCHANGE_INTERNAL_NAME] = {}
    exchange_manager = trading_exchanges.ExchangeManager(config, EXCHANGE_INTERNAL_NAME)
    exchange_manager.exchange_only = True
    await exchange_manager.initialize(exchange_config_by_exchange=None)
    try:
        yield exchange_manager
    finally:
        await exchange_manager.stop()
        trading_api.cancel_ccxt_throttle_task()
        await asyncio_tools.wait_asyncio_next_cycle()


async def assert_coinrabbit_markets_expose_symbols(
    exchange_manager: trading_exchanges.ExchangeManager,
    required_symbols: typing.Sequence[str] = REQUIRED_MARKET_SYMBOLS,  # noqa: UP006
) -> None:
    available = set(trading_api.get_all_available_symbols(exchange_manager))
    for symbol in required_symbols:
        assert symbol in available, (
            f"{symbol!r} missing from get_all_available_symbols; sample: {sorted(available)[:12]}"
        )
        market_status = exchange_manager.exchange.get_market_status(symbol, with_fixer=False)
        info = market_status.get(trading_enums.ExchangeConstantsMarketStatusColumns.INFO.value, {})
        assert info.get("base_network"), f"market info must preserve base_network for {symbol}"
        assert info.get("quote_network"), f"market info must preserve quote_network for {symbol}"
    parsed = commons_symbols.parse_symbol(TRADED_PAIR)
    assert parsed.has_ticker_wise_networks() is True


def tickers_repository_fetch_tickers_close_override(
    close_by_symbol: dict[str, float],
):
    close_col = trading_enums.ExchangeConstantsTickersColumns.CLOSE.value

    async def patched_fetch_tickers(self, symbols):
        if symbols == []:
            return {}
        if isinstance(symbols, list):
            return {
                symbol: {close_col: close_by_symbol[symbol]}
                for symbol in symbols
                if symbol in close_by_symbol
            }
        return {
            symbol: {close_col: close_value}
            for symbol, close_value in close_by_symbol.items()
        }

    return patched_fetch_tickers


def _mock_tickers_for_symbols(
    symbols: typing.Optional[list[str]],
    close_by_symbol: dict[str, float],
) -> dict[str, dict]:
    close_col = trading_enums.ExchangeConstantsTickersColumns.CLOSE.value
    if symbols:
        return {
            symbol: {close_col: close_by_symbol[symbol]}
            for symbol in symbols
            if symbol in close_by_symbol
        }
    return {symbol: {close_col: close} for symbol, close in close_by_symbol.items()}


def _fetch_ohlcv_side_effect_for_close_prices(close_by_symbol: dict[str, float]):
    async def patched_fetch_ohlcv(
        symbol: str,
        time_frame: str,
        limit: int,
        _tickers: dict[str, dict[str, typing.Any]],
    ):
        time_frame_seconds = common_enums.TimeFramesMinutes[common_enums.TimeFrames(time_frame)] * 60
        close_price = float(close_by_symbol.get(symbol, next(iter(close_by_symbol.values()))))
        candle_count = max(int(limit or 1), 1)
        local_time = time.time()
        current_candle_open_time = local_time - (local_time % time_frame_seconds)
        first_candle_open_time = current_candle_open_time - (candle_count - 1) * time_frame_seconds
        times = [float(first_candle_open_time + index * time_frame_seconds) for index in range(candle_count)]
        closes = [close_price] * candle_count
        return exchange_data.MarketDetails(
            symbol=symbol,
            time_frame=time_frame,
            close=closes,
            open=closes,
            high=closes,
            low=closes,
            volume=[0.0] * candle_count,
            time=times,
        )

    return patched_fetch_ohlcv


@contextlib.contextmanager
def patch_coinrabbit_ticker_closes(close_by_symbol: dict[str, float] | None = None):
    prices = close_by_symbol or MOCK_CLOSE_BY_SYMBOL
    patched_fetch_tickers_impl = tickers_repository_fetch_tickers_close_override(prices)
    patched_fetch_ohlcv_impl = _fetch_ohlcv_side_effect_for_close_prices(prices)

    async def tracked_fetch_tickers(self, symbols):
        return await patched_fetch_tickers_impl(self, symbols)

    async def tracked_fetch_all_tickers(self, symbols):
        return _mock_tickers_for_symbols(symbols, prices)

    async def tracked_fetch_ohlcv(self, symbol, time_frame, limit, tickers):
        return await patched_fetch_ohlcv_impl(symbol, time_frame, limit, tickers)

    import octobot_trading.exchange_data.ticker.channel.ticker_updater as ticker_updater_module

    close_col = trading_enums.ExchangeConstantsTickersColumns.CLOSE.value
    orig_get_all_tickers = exchanges_test_tools.get_all_currencies_price_ticker
    orig_get_price_ticker = exchanges_test_tools.get_price_ticker
    orig_get_up_to_date_price = trading_personal_data.get_up_to_date_price

    async def patched_get_all_currencies_price_ticker(exchange_manager, **kwargs):
        tickers = await orig_get_all_tickers(exchange_manager, **kwargs)
        for symbol, close_value in prices.items():
            if symbol in tickers:
                tickers[symbol] = {**tickers[symbol], close_col: close_value}
            else:
                tickers[symbol] = {close_col: close_value}
        return tickers

    async def patched_get_price_ticker(exchange_manager, symbol: str, **kwargs):
        if symbol in prices:
            return {close_col: prices[symbol]}
        return await orig_get_price_ticker(exchange_manager, symbol, **kwargs)

    async def patched_get_up_to_date_price(exchange_manager, symbol: str, **kwargs):
        if symbol in prices:
            return decimal.Decimal(str(prices[symbol]))
        return await orig_get_up_to_date_price(exchange_manager, symbol, **kwargs)

    with (
        mock.patch.object(
            exchange_repositories.TickersRepository,
            "fetch_tickers",
            new=tracked_fetch_tickers,
        ),
        mock.patch.object(
            exchange_repositories.OhlcvRepository,
            "fetch_ohlcv",
            new=tracked_fetch_ohlcv,
        ),
        mock.patch.object(
            ticker_updater_module.TickerUpdater,
            "fetch_all_tickers",
            new=tracked_fetch_all_tickers,
        ),
        mock.patch.object(
            exchanges_test_tools,
            "get_all_currencies_price_ticker",
            new=patched_get_all_currencies_price_ticker,
        ),
        mock.patch.object(
            exchanges_test_tools,
            "get_price_ticker",
            new=patched_get_price_ticker,
        ),
        mock.patch.object(
            trading_personal_data,
            "get_up_to_date_price",
            new=patched_get_up_to_date_price,
        ),
    ):
        yield
