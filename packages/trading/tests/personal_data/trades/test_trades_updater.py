import mock
import pytest

import octobot_trading.personal_data.trades.channel.trades_updater as trades_updater_module


class TestTradesUpdaterFetchTrades:
    @pytest.mark.asyncio
    async def test_fetch_trades_single_symbol(self):
        updater = mock.MagicMock()
        updater.channel.exchange_manager.exchange.get_my_recent_trades = mock.AsyncMock(
            return_value=[{"id": "trade-1"}]
        )
        result = await trades_updater_module.TradesUpdater.fetch_trades(
            updater, ["BTC/USDT"], limit=50
        )
        assert result == [{"id": "trade-1"}]
        updater.channel.exchange_manager.exchange.get_my_recent_trades.assert_awaited_once_with(
            symbol="BTC/USDT", limit=50
        )

    @pytest.mark.asyncio
    async def test_fetch_trades_multiple_symbols(self):
        updater = mock.MagicMock()

        async def get_my_recent_trades(symbol, limit):
            return [{"id": symbol}]

        updater.channel.exchange_manager.exchange.get_my_recent_trades = get_my_recent_trades
        result = await trades_updater_module.TradesUpdater.fetch_trades(
            updater, ["BTC/USDT", "ETH/USDT"]
        )
        assert result == [{"id": "BTC/USDT"}, {"id": "ETH/USDT"}]

    @pytest.mark.asyncio
    async def test_fetch_trades_empty_symbols(self):
        updater = mock.MagicMock()
        result = await trades_updater_module.TradesUpdater.fetch_trades(updater, [])
        assert result == []


class TestTradesUpdaterFetchTradesExhaustHistory:
    @pytest.mark.asyncio
    async def test_fetch_trades_exhaust_history_single_symbol(self):
        updater = mock.MagicMock()
        updater.channel.exchange_manager.exchange.get_my_recent_trades = mock.AsyncMock(
            return_value=[{"id": "trade-1"}]
        )
        result = await trades_updater_module.TradesUpdater.fetch_trades(
            updater, ["BTC/USDT"], exhaust_history=True,
        )
        assert result == [{"id": "trade-1"}]
        updater.channel.exchange_manager.exchange.get_my_recent_trades.assert_awaited_once_with(
            symbol="BTC/USDT", exhaust_history=True,
        )

    @pytest.mark.asyncio
    async def test_fetch_trades_exhaust_history_multiple_symbols(self):
        updater = mock.MagicMock()

        async def get_my_recent_trades(symbol, exhaust_history=False, limit=None):
            return [{"id": symbol}]

        updater.channel.exchange_manager.exchange.get_my_recent_trades = get_my_recent_trades
        result = await trades_updater_module.TradesUpdater.fetch_trades(
            updater, ["BTC/USDT", "ETH/USDT"], exhaust_history=True,
        )
        assert result == [{"id": "BTC/USDT"}, {"id": "ETH/USDT"}]

    @pytest.mark.asyncio
    async def test_fetch_trades_exhaust_history_account_wide(self):
        updater = mock.MagicMock()
        updater.channel.exchange_manager.exchange.get_my_recent_trades = mock.AsyncMock(
            return_value=[{"id": "trade-1"}]
        )
        result = await trades_updater_module.TradesUpdater.fetch_trades(
            updater, [], exhaust_history=True,
        )
        assert result == [{"id": "trade-1"}]
        updater.channel.exchange_manager.exchange.get_my_recent_trades.assert_awaited_once_with(
            symbol=None, exhaust_history=True,
        )

    @pytest.mark.asyncio
    async def test_fetch_trades_empty_symbols_without_exhaust_returns_empty(self):
        updater = mock.MagicMock()
        updater.channel.exchange_manager.exchange.get_my_recent_trades = mock.AsyncMock()
        result = await trades_updater_module.TradesUpdater.fetch_trades(updater, [])
        assert result == []
        updater.channel.exchange_manager.exchange.get_my_recent_trades.assert_not_called()


class TestTradesUpdaterFetchTradesSince:
    @pytest.mark.asyncio
    async def test_single_symbol_passes_since(self):
        updater = mock.MagicMock()
        updater.channel.exchange_manager.exchange.get_my_recent_trades = mock.AsyncMock(
            return_value=[{"id": "trade-1"}]
        )
        result = await trades_updater_module.TradesUpdater.fetch_trades(
            updater,
            ["BTC/USDT"],
            since=1_700_000_000_000,
        )
        assert result == [{"id": "trade-1"}]
        updater.channel.exchange_manager.exchange.get_my_recent_trades.assert_awaited_once_with(
            symbol="BTC/USDT",
            since=1_700_000_000_000,
            limit=trades_updater_module.TradesUpdater.MAX_OLD_TRADES_TO_FETCH,
        )

    @pytest.mark.asyncio
    async def test_since_and_exhaust_history_both_forwarded(self):
        updater = mock.MagicMock()
        updater.channel.exchange_manager.exchange.get_my_recent_trades = mock.AsyncMock(
            return_value=[{"id": "trade-1"}]
        )
        await trades_updater_module.TradesUpdater.fetch_trades(
            updater,
            ["BTC/USDT"],
            since=1_700_000_000_000,
            exhaust_history=True,
        )
        updater.channel.exchange_manager.exchange.get_my_recent_trades.assert_awaited_once_with(
            symbol="BTC/USDT",
            since=1_700_000_000_000,
            exhaust_history=True,
        )

    @pytest.mark.asyncio
    async def test_since_none_omits_param(self):
        updater = mock.MagicMock()
        updater.channel.exchange_manager.exchange.get_my_recent_trades = mock.AsyncMock(
            return_value=[{"id": "trade-1"}]
        )
        await trades_updater_module.TradesUpdater.fetch_trades(
            updater,
            ["BTC/USDT"],
            limit=50,
        )
        updater.channel.exchange_manager.exchange.get_my_recent_trades.assert_awaited_once_with(
            symbol="BTC/USDT",
            limit=50,
        )


class TestTradesUpdaterFetchTradesSinceMultipleSymbols:
    @pytest.mark.asyncio
    async def test_each_symbol_receives_shared_since(self):
        updater = mock.MagicMock()
        received_calls: list[dict] = []

        async def get_my_recent_trades(symbol, since=None, exhaust_history=False, limit=None):
            received_calls.append({
                "symbol": symbol,
                "since": since,
                "exhaust_history": exhaust_history,
                "limit": limit,
            })
            return [{"id": symbol}]

        updater.channel.exchange_manager.exchange.get_my_recent_trades = get_my_recent_trades
        result = await trades_updater_module.TradesUpdater.fetch_trades(
            updater,
            ["BTC/USDT", "ETH/USDT"],
            since=1_700_000_000_000,
            exhaust_history=True,
        )
        assert result == [{"id": "BTC/USDT"}, {"id": "ETH/USDT"}]
        assert received_calls == [
            {
                "symbol": "BTC/USDT",
                "since": 1_700_000_000_000,
                "exhaust_history": True,
                "limit": None,
            },
            {
                "symbol": "ETH/USDT",
                "since": 1_700_000_000_000,
                "exhaust_history": True,
                "limit": None,
            },
        ]


class TestTradesUpdaterFetchTradesSinceAccountWide:
    @pytest.mark.asyncio
    async def test_account_wide_passes_since(self):
        updater = mock.MagicMock()
        updater.channel.exchange_manager.exchange.get_my_recent_trades = mock.AsyncMock(
            return_value=[{"id": "trade-1"}]
        )
        result = await trades_updater_module.TradesUpdater.fetch_trades(
            updater,
            [],
            since=1_700_000_000_000,
            exhaust_history=True,
        )
        assert result == [{"id": "trade-1"}]
        updater.channel.exchange_manager.exchange.get_my_recent_trades.assert_awaited_once_with(
            symbol=None,
            since=1_700_000_000_000,
            exhaust_history=True,
        )


class TestTradesUpdaterFetchAndPush:
    @pytest.mark.asyncio
    async def test_fetch_and_push_uses_fetch_trades(self):
        updater = mock.MagicMock()
        updater.logger = mock.MagicMock()
        updater.MAX_OLD_TRADES_TO_FETCH = trades_updater_module.TradesUpdater.MAX_OLD_TRADES_TO_FETCH
        updater._get_pairs_to_update = mock.Mock(return_value=["BTC/USDT"])
        updater.fetch_trades = mock.AsyncMock(return_value=[{"id": "trade-1"}])
        updater.push = mock.AsyncMock()

        await trades_updater_module.TradesUpdater.fetch_and_push(updater)

        updater.fetch_trades.assert_awaited_once_with(
            ["BTC/USDT"], limit=trades_updater_module.TradesUpdater.MAX_OLD_TRADES_TO_FETCH
        )
        updater.channel.exchange_manager.exchange.get_my_recent_trades.assert_not_called()
        updater.push.assert_awaited_once_with([{"id": "trade-1"}])

    @pytest.mark.asyncio
    async def test_fetch_and_push_iterates_all_symbols(self):
        updater = mock.MagicMock()
        updater.logger = mock.MagicMock()
        updater.MAX_OLD_TRADES_TO_FETCH = trades_updater_module.TradesUpdater.MAX_OLD_TRADES_TO_FETCH
        updater._get_pairs_to_update = mock.Mock(return_value=["BTC/USDT", "ETH/USDT"])
        updater.fetch_trades = mock.AsyncMock(side_effect=[
            [{"id": "btc-trade"}],
            [{"id": "eth-trade"}],
        ])
        updater.push = mock.AsyncMock()

        await trades_updater_module.TradesUpdater.fetch_and_push(updater)

        trades_fetch_limit = trades_updater_module.TradesUpdater.MAX_OLD_TRADES_TO_FETCH
        assert updater.fetch_trades.await_args_list == [
            mock.call(["BTC/USDT"], limit=trades_fetch_limit),
            mock.call(["ETH/USDT"], limit=trades_fetch_limit),
        ]
        assert updater.push.await_args_list == [
            mock.call([{"id": "btc-trade"}]),
            mock.call([{"id": "eth-trade"}]),
        ]

    @pytest.mark.asyncio
    async def test_fetch_and_push_skips_empty_symbol(self):
        updater = mock.MagicMock()
        updater.logger = mock.MagicMock()
        updater.MAX_OLD_TRADES_TO_FETCH = trades_updater_module.TradesUpdater.MAX_OLD_TRADES_TO_FETCH
        updater._get_pairs_to_update = mock.Mock(return_value=["BTC/USDT", "ETH/USDT"])
        updater.fetch_trades = mock.AsyncMock(side_effect=[
            [{"id": "btc-trade"}],
            [],
        ])
        updater.push = mock.AsyncMock()

        await trades_updater_module.TradesUpdater.fetch_and_push(updater)

        updater.push.assert_awaited_once_with([{"id": "btc-trade"}])


class TestTradesUpdaterEnsureParsing:
    def test_returns_parsed_trade_dict(self):
        exchange_manager = mock.MagicMock()
        exchange_manager.exchange_name = "binance"
        parsed_trade = mock.MagicMock()
        parsed_trade.to_dict.return_value = {"id": "trade-1"}
        with mock.patch(
            "octobot_trading.personal_data.trades.trade_factory.create_trade_instance_from_raw",
            return_value=parsed_trade,
        ) as create_trade_mock:
            result = trades_updater_module.TradesUpdater.ensure_parsing(
                exchange_manager, {"id": "trade-1"}
            )
        create_trade_mock.assert_called_once_with(exchange_manager.trader, {"id": "trade-1"})
        assert result == {"id": "trade-1"}

    def test_returns_none_on_parse_error(self):
        exchange_manager = mock.MagicMock()
        exchange_manager.exchange_name = "binance"
        with mock.patch(
            "octobot_trading.personal_data.trades.trade_factory.create_trade_instance_from_raw",
            side_effect=ValueError("bad trade"),
        ):
            result = trades_updater_module.TradesUpdater.ensure_parsing(
                exchange_manager, {"id": "bad"}
            )
        assert result is None
