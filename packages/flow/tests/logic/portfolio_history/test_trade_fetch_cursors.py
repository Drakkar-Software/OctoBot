import datetime

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models
import octobot_trading.enums as trading_enums

import octobot_flow.constants as flow_constants
import octobot_flow.logic.portfolio_history.trade_fetch_cursors as trade_fetch_cursors_module

_TEST_TIMESTAMP = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)


def _empty_daily_prices():
    return {
        trading_enums.DailyPricesCacheKeys.SYMBOLS: {},
        trading_enums.DailyPricesCacheKeys.SOURCES: {},
    }


def _make_trade(symbol: str) -> protocol_models.Trade:
    return protocol_models.Trade(
        id=f"trade-{symbol}",
        trade_id=f"trade-{symbol}",
        type=protocol_models.OrderType.LIMIT,
        symbol=symbol,
        side=protocol_models.Side.BUY,
        quantity=1.0,
        price=1.0,
        status=protocol_models.OrderStatus.FILLED,
        executed_at=_TEST_TIMESTAMP,
    )


def _make_account_trading(symbols: list[str] | None) -> protocol_models.AccountTrading:
    if symbols is None:
        return protocol_models.AccountTrading(
            updated_at=_TEST_TIMESTAMP,
            trades=None,
        )
    return protocol_models.AccountTrading(
        updated_at=_TEST_TIMESTAMP,
        trades=[_make_trade(symbol) for symbol in symbols],
    )


class TestSymbolsWithPersistedTrades:
    def test_returns_empty_when_account_trading_is_none(self):
        assert trade_fetch_cursors_module.symbols_with_persisted_trades(None) == set()

    def test_returns_empty_when_trades_is_none(self):
        account_trading = _make_account_trading(None)
        assert trade_fetch_cursors_module.symbols_with_persisted_trades(account_trading) == set()

    def test_returns_single_symbol(self):
        account_trading = _make_account_trading(["BTC/USDT"])
        assert trade_fetch_cursors_module.symbols_with_persisted_trades(account_trading) == {"BTC/USDT"}

    def test_returns_multiple_symbols(self):
        account_trading = _make_account_trading(["BTC/USDT", "ETH/USDT"])
        assert trade_fetch_cursors_module.symbols_with_persisted_trades(account_trading) == {
            "BTC/USDT",
            "ETH/USDT",
        }

    def test_ignores_trades_without_symbol(self):
        account_trading = protocol_models.AccountTrading(
            updated_at=_TEST_TIMESTAMP,
            trades=[
                _make_trade("BTC/USDT"),
                protocol_models.Trade(
                    id="trade-missing-symbol",
                    trade_id="trade-missing-symbol",
                    type=protocol_models.OrderType.LIMIT,
                    symbol="",
                    side=protocol_models.Side.BUY,
                    quantity=1.0,
                    price=1.0,
                    status=protocol_models.OrderStatus.FILLED,
                    executed_at=_TEST_TIMESTAMP,
                ),
            ],
        )
        assert trade_fetch_cursors_module.symbols_with_persisted_trades(account_trading) == {"BTC/USDT"}


def _expected_since_ms(day_timestamp: int) -> int:
    return int(
        (
            day_timestamp
            - flow_constants.PORTFOLIO_HISTORY_TRADE_FETCH_SINCE_LOOKBACK_DAYS
            * commons_constants.DAYS_TO_SECONDS
        )
        * 1000
    )


class TestGetGlobalLatestDailyPriceTimestamp:
    def test_returns_none_for_empty_cache(self):
        assert trade_fetch_cursors_module.get_global_latest_daily_price_timestamp(
            _empty_daily_prices(),
        ) is None

    def test_returns_max_newest_timestamp_across_symbols(self):
        daily_prices = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {
                "BTC/USDT": {"1000": 42000.0, "2000": 43000.0},
                "ETH/USDT": {"1500": 2500.0, "3000": 2600.0},
            },
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        assert trade_fetch_cursors_module.get_global_latest_daily_price_timestamp(
            daily_prices,
        ) == 3000.0


class TestUsesGlobalDailyPriceCursor:
    def test_returns_true_for_usd_like_pair_with_global_cache(self):
        daily_prices = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"2000": 43000.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        assert trade_fetch_cursors_module.uses_global_daily_price_cursor(
            daily_prices,
            "USDC/USDT",
        )

    def test_returns_false_when_direct_cache_exists(self):
        daily_prices = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"USDC/USDT": {"2000": 1.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        assert not trade_fetch_cursors_module.uses_global_daily_price_cursor(
            daily_prices,
            "USDC/USDT",
        )

    def test_returns_false_for_usdc_eur_with_global_cache(self):
        daily_prices = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"2000": 43000.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        assert not trade_fetch_cursors_module.uses_global_daily_price_cursor(
            daily_prices,
            "USDC/EUR",
        )

    def test_returns_false_for_usd_like_pair_with_empty_cache(self):
        assert not trade_fetch_cursors_module.uses_global_daily_price_cursor(
            _empty_daily_prices(),
            "USDC/USD",
        )


class TestResolveDailyCacheSymbol:
    def test_returns_trade_symbol_when_direct_cache_hit(self):
        daily_prices = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"1700000000": 42000.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        assert trade_fetch_cursors_module.resolve_daily_cache_symbol(
            daily_prices,
            "BTC/USDT",
        ) == "BTC/USDT"

    def test_returns_sticky_source_when_trade_symbol_missing(self):
        daily_prices = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"KNC/USDC": {"1700000000": 1.2}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {"KNC": "KNC/USDC"},
        }
        assert trade_fetch_cursors_module.resolve_daily_cache_symbol(
            daily_prices,
            "KNC/USD",
        ) == "KNC/USDC"

    def test_returns_none_when_no_cache_entry(self):
        daily_prices = _empty_daily_prices()
        assert trade_fetch_cursors_module.resolve_daily_cache_symbol(
            daily_prices,
            "BTC/USDT",
        ) is None


class TestComputeTradeFetchSinceMs:
    def test_returns_none_when_no_candle(self):
        daily_prices = _empty_daily_prices()
        assert trade_fetch_cursors_module.compute_trade_fetch_since_ms(
            daily_prices,
            "BTC/USDT",
        ) is None

    def test_uses_newest_minus_two_days(self):
        daily_prices = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"1000": 42000.0, "2000": 43000.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        since_ms = trade_fetch_cursors_module.compute_trade_fetch_since_ms(
            daily_prices,
            "BTC/USDT",
        )
        expected_since_ms = int(
            (
                2000
                - flow_constants.PORTFOLIO_HISTORY_TRADE_FETCH_SINCE_LOOKBACK_DAYS
                * commons_constants.DAYS_TO_SECONDS
            )
            * 1000
        )
        assert since_ms == expected_since_ms

    def test_uses_resolved_cache_symbol(self):
        daily_prices = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"KNC/USDC": {"3000": 1.1}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {"KNC": "KNC/USDC"},
        }
        since_ms = trade_fetch_cursors_module.compute_trade_fetch_since_ms(
            daily_prices,
            "KNC/USD",
        )
        expected_since_ms = int(
            (
                3000
                - flow_constants.PORTFOLIO_HISTORY_TRADE_FETCH_SINCE_LOOKBACK_DAYS
                * commons_constants.DAYS_TO_SECONDS
            )
            * 1000
        )
        assert since_ms == expected_since_ms

    def test_uses_global_cache_for_usd_like_pair(self):
        daily_prices = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"4000": 42000.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        since_ms = trade_fetch_cursors_module.compute_trade_fetch_since_ms(
            daily_prices,
            "USDC/USDT",
        )
        assert since_ms == _expected_since_ms(4000)

    def test_returns_none_for_usd_like_pair_with_empty_cache(self):
        assert trade_fetch_cursors_module.compute_trade_fetch_since_ms(
            _empty_daily_prices(),
            "USDC/USDT",
        ) is None

    def test_returns_none_for_usdc_eur_with_only_global_cache(self):
        daily_prices = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"4000": 42000.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        assert trade_fetch_cursors_module.compute_trade_fetch_since_ms(
            daily_prices,
            "USDC/EUR",
        ) is None


class TestBuildSymbolSinceMs:
    def test_omits_symbol_without_persisted_trades(self):
        daily_prices = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"2000": 43000.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        assert trade_fetch_cursors_module.build_symbol_since_ms(
            ["BTC/USDT"],
            _make_account_trading([]),
            daily_prices,
        ) == {}

    def test_includes_symbol_with_persisted_trades_and_candle(self):
        daily_prices = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"2000": 43000.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        symbol_since_ms = trade_fetch_cursors_module.build_symbol_since_ms(
            ["BTC/USDT"],
            _make_account_trading(["BTC/USDT"]),
            daily_prices,
        )
        expected_since_ms = int(
            (
                2000
                - flow_constants.PORTFOLIO_HISTORY_TRADE_FETCH_SINCE_LOOKBACK_DAYS
                * commons_constants.DAYS_TO_SECONDS
            )
            * 1000
        )
        assert symbol_since_ms == {"BTC/USDT": expected_since_ms}

    def test_omits_symbol_with_persisted_trades_but_no_candle(self):
        assert trade_fetch_cursors_module.build_symbol_since_ms(
            ["BTC/USDT"],
            _make_account_trading(["BTC/USDT"]),
            _empty_daily_prices(),
        ) == {}

    def test_only_includes_discovered_symbols(self):
        daily_prices = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {
                "BTC/USDT": {"2000": 43000.0},
                "ETH/USDT": {"2000": 2500.0},
            },
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        symbol_since_ms = trade_fetch_cursors_module.build_symbol_since_ms(
            ["BTC/USDT"],
            _make_account_trading(["BTC/USDT", "ETH/USDT"]),
            daily_prices,
        )
        assert set(symbol_since_ms) == {"BTC/USDT"}

    def test_returns_empty_map_when_account_trading_is_none(self):
        daily_prices = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"2000": 43000.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        assert trade_fetch_cursors_module.build_symbol_since_ms(
            ["BTC/USDT"],
            None,
            daily_prices,
        ) == {}

    def test_includes_usd_like_pair_using_global_cache(self):
        daily_prices = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"ETH/USDT": {"5000": 2500.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        symbol_since_ms = trade_fetch_cursors_module.build_symbol_since_ms(
            ["USDC/USD"],
            _make_account_trading(["USDC/USD"]),
            daily_prices,
        )
        assert symbol_since_ms == {"USDC/USD": _expected_since_ms(5000)}

    def test_omits_usd_like_pair_when_cache_is_empty(self):
        assert trade_fetch_cursors_module.build_symbol_since_ms(
            ["USDC/USDT"],
            _make_account_trading(["USDC/USDT"]),
            _empty_daily_prices(),
        ) == {}
