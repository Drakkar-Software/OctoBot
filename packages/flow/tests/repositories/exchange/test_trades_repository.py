import mock
import pytest

import octobot_flow.repositories.exchange.trades_repository as trades_repository_module
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data as trading_personal_data


def _make_repo(exchange_manager):
    fetched_data = mock.MagicMock()
    return trades_repository_module.TradesRepository(exchange_manager, [], fetched_data)


def _allow_all_symbols(exchange_manager):
    exchange_manager.symbol_exists.return_value = True
    return exchange_manager


class TestTradesRepositoryFetchTrades:
    @pytest.mark.asyncio
    async def test_uses_updater_fetch_and_ensure_parsing(self):
        exchange_manager = _allow_all_symbols(mock.MagicMock())
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.return_value = [{"id": "raw-trade-1", "symbol": "BTC/USDT"}]
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                return_value={"id": "parsed-trade-1"},
            ) as ensure_parsing_mock,
        ):
            result = await repo.fetch_trades(["BTC/USDT"])

        updater.fetch_trades.assert_awaited_once_with(["BTC/USDT"])
        ensure_parsing_mock.assert_called_once_with(
            exchange_manager,
            {"id": "raw-trade-1", "symbol": "BTC/USDT"},
        )
        assert result == [{"id": "parsed-trade-1"}]

    @pytest.mark.asyncio
    async def test_empty_symbols_returns_empty_list(self):
        repo = _make_repo(mock.MagicMock())
        assert await repo.fetch_trades([]) == []


class TestFetchTradesPaginatedClientSideFilter:
    @pytest.mark.asyncio
    async def test_bulk_fetch_single_call_when_client_side_filter_enabled(self):
        exchange_manager = _allow_all_symbols(mock.MagicMock())
        exchange_manager.exchange.get_option_value.return_value = True
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.return_value = [
            {"id": "trade-1", "symbol": "ALGO/USDC", "timestamp": 1700000000.0},
            {"id": "trade-2", "symbol": "SOL/USDC", "timestamp": 1700000001.0},
        ]
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                side_effect=lambda _exchange_manager, raw_trade: raw_trade,
            ),
        ):
            result = await repo.fetch_trades_paginated(
                ["ALGO/USDC", "SOL/USDC"],
                existing_config_symbols=set(),
                exchange_name="kraken",
                account_id="acc-1",
                exchange_config_id="cfg-1",
                exchange_config_name="cfg-name",
            )

        updater.fetch_trades.assert_awaited_once_with([], exhaust_history=True)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_bulk_fetch_logs_per_symbol_counts(self, caplog):
        import logging
        caplog.set_level(logging.INFO)
        exchange_manager = _allow_all_symbols(mock.MagicMock())
        exchange_manager.exchange.get_option_value.return_value = True
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.return_value = [
            {"id": "trade-1", "symbol": "ALGO/USDC", "timestamp": 1700000000.0},
        ]
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                side_effect=lambda _exchange_manager, raw_trade: raw_trade,
            ),
        ):
            await repo.fetch_trades_paginated(
                ["ALGO/USDC", "SOL/USDC"],
                existing_config_symbols={"ALGO/USDC"},
                exchange_name="kraken",
                account_id="acc-1",
                exchange_config_id="cfg-1",
                exchange_config_name="cfg-name",
            )

        assert "Fetched 1 trades for ALGO/USDC on kraken" in caplog.text
        assert "Fetched 0 trades for SOL/USDC on kraken" in caplog.text


class TestFetchTradesPaginatedPerSymbol:
    @pytest.mark.asyncio
    async def test_fetches_one_call_per_symbol_when_client_side_filter_disabled(self):
        exchange_manager = _allow_all_symbols(mock.MagicMock())
        exchange_manager.exchange.get_option_value.return_value = False
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.return_value = [
            {"id": "trade-1", "timestamp": 1700000000.0, "symbol": "BTC/USDT"},
        ]
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                side_effect=lambda _exchange_manager, raw_trade: raw_trade,
            ),
        ):
            result = await repo.fetch_trades_paginated(
                ["BTC/USDT"],
                existing_config_symbols=set(),
                exchange_name="binance",
                account_id="acc-1",
                exchange_config_id="cfg-1",
                exchange_config_name="cfg-name",
            )

        updater.fetch_trades.assert_awaited_once_with(
            ["BTC/USDT"],
            exhaust_history=True,
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_multiple_symbols_single_batch_fetch(self):
        exchange_manager = _allow_all_symbols(mock.MagicMock())
        exchange_manager.exchange.get_option_value.return_value = False
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.return_value = []
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                side_effect=lambda _exchange_manager, raw_trade: raw_trade,
            ),
        ):
            await repo.fetch_trades_paginated(
                ["BTC/USDT", "ETH/USDT"],
                existing_config_symbols={"BTC/USDT"},
                exchange_name="binance",
                account_id="acc-1",
                exchange_config_id="cfg-1",
                exchange_config_name="cfg-name",
            )

        updater.fetch_trades.assert_awaited_once_with(
            ["BTC/USDT", "ETH/USDT"],
            exhaust_history=True,
        )

    @pytest.mark.asyncio
    async def test_exhaust_history_when_ccxt_paginate_option_enabled(self):
        exchange_manager = _allow_all_symbols(mock.MagicMock())

        def get_option_value(option_key):
            if option_key == trading_enums.ExchangeClientOptions.MY_TRADES_SYMBOL_FILTER_IS_CLIENT_SIDE:
                return False
            if option_key == trading_enums.ExchangeClientOptions.MY_TRADES_FETCH_USE_CCXT_PAGINATE:
                return True
            return trading_enums.DEFAULT_EXCHANGE_OPTION_VALUES.get(option_key)

        exchange_manager.exchange.get_option_value = get_option_value
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.return_value = [
            {"id": "trade-1", "timestamp": 1700000000.0, "symbol": "BTC/USDT"},
        ]
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                side_effect=lambda _exchange_manager, raw_trade: raw_trade,
            ),
        ):
            await repo.fetch_trades_paginated(
                ["BTC/USDT"],
                existing_config_symbols=set(),
                exchange_name="binance",
                account_id="acc-1",
                exchange_config_id="cfg-1",
                exchange_config_name="cfg-name",
            )

        updater.fetch_trades.assert_awaited_once_with(
            ["BTC/USDT"],
            exhaust_history=True,
        )

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_symbol_list(self):
        repo = _make_repo(mock.MagicMock())
        result = await repo.fetch_trades_paginated(
            [],
            existing_config_symbols=set(),
            exchange_name="binance",
            account_id="acc-1",
            exchange_config_id="cfg-1",
            exchange_config_name="cfg-name",
        )
        assert result == []


class TestTradesRepositorySkipsDelistedBeforeParsing:
    @pytest.mark.asyncio
    async def test_bulk_fetch_skips_parsing_for_delisted_symbols(self):
        exchange_manager = mock.MagicMock()
        exchange_manager.symbol_exists.side_effect = lambda symbol: symbol == "ALGO/USDC"
        exchange_manager.exchange.get_option_value.return_value = True
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.return_value = [
            {"id": "trade-1", "symbol": "ALGO/USDC", "timestamp": 1700000000.0},
            {"id": "trade-2", "symbol": "MATICXBT", "timestamp": 1700000001.0},
        ]
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                side_effect=lambda _exchange_manager, raw_trade: raw_trade,
            ) as ensure_parsing_mock,
        ):
            result = await repo.fetch_trades_paginated(
                ["ALGO/USDC"],
                existing_config_symbols=set(),
                exchange_name="kraken",
                account_id="acc-1",
                exchange_config_id="cfg-1",
                exchange_config_name="cfg-name",
            )

        ensure_parsing_mock.assert_called_once_with(
            exchange_manager,
            {"id": "trade-1", "symbol": "ALGO/USDC", "timestamp": 1700000000.0},
        )
        assert len(result) == 1
        assert result[0]["symbol"] == "ALGO/USDC"

    @pytest.mark.asyncio
    async def test_bulk_fetch_logs_skipped_delisted_symbols(self, caplog):
        import logging

        caplog.set_level(logging.INFO)
        exchange_manager = mock.MagicMock()
        exchange_manager.symbol_exists.side_effect = lambda symbol: symbol == "ALGO/USDC"
        exchange_manager.exchange.get_option_value.return_value = True
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.return_value = [
            {"id": "trade-1", "symbol": "ALGO/USDC", "timestamp": 1700000000.0},
            {"id": "trade-2", "symbol": "MATICXBT", "timestamp": 1700000001.0},
            {"id": "trade-3", "symbol": "FTMEUR", "timestamp": 1700000002.0},
        ]
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                side_effect=lambda _exchange_manager, raw_trade: raw_trade,
            ),
        ):
            await repo.fetch_trades_paginated(
                ["ALGO/USDC"],
                existing_config_symbols=set(),
                exchange_name="kraken",
                account_id="acc-1",
                exchange_config_id="cfg-1",
                exchange_config_name="cfg-name",
            )

        assert "Skipped 2 trades on delisted/unknown markets before parsing" in caplog.text
        assert "MATICXBT" in caplog.text
        assert "FTMEUR" in caplog.text


class TestTradesRepositoryEnsureTemporaryTradesChannel:
    @pytest.mark.asyncio
    async def test_creates_channels_and_trades_producer_only(self):
        exchange_manager = mock.Mock()
        with (
            mock.patch(
                "octobot_trading.exchanges.create_exchange_channels",
                mock.AsyncMock(),
            ) as create_exchange_channels_mock,
            mock.patch(
                "octobot_trading.exchanges.create_producers",
                mock.AsyncMock(),
            ) as create_producers_mock,
        ):
            await trades_repository_module.TradesRepository.ensure_temporary_trades_channel(exchange_manager)

        create_exchange_channels_mock.assert_awaited_once_with(exchange_manager)
        create_producers_mock.assert_awaited_once_with(
            exchange_manager,
            [trading_personal_data.TradesUpdater],
            start_producers=False,
        )


class TestFetchTradesPaginatedIncrementalPerSymbol:
    @pytest.mark.asyncio
    async def test_incremental_symbol_uses_since_and_exhaust_history(self):
        exchange_manager = _allow_all_symbols(mock.MagicMock())
        exchange_manager.exchange.get_option_value.return_value = False
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.return_value = [
            {"id": "trade-1", "timestamp": 1700000000.0, "symbol": "BTC/USDT"},
        ]
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                side_effect=lambda _exchange_manager, raw_trade: raw_trade,
            ),
        ):
            await repo.fetch_trades_paginated(
                ["BTC/USDT"],
                existing_config_symbols=set(),
                exchange_name="binance",
                account_id="acc-1",
                exchange_config_id="cfg-1",
                exchange_config_name="cfg-name",
                symbol_since_ms={"BTC/USDT": 1_700_000_000_000},
            )

        updater.fetch_trades.assert_awaited_once_with(
            ["BTC/USDT"],
            since=1_700_000_000_000,
            exhaust_history=True,
        )

    @pytest.mark.asyncio
    async def test_full_symbol_uses_exhaust_history_without_since(self):
        exchange_manager = _allow_all_symbols(mock.MagicMock())
        exchange_manager.exchange.get_option_value.return_value = False
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.return_value = []
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                side_effect=lambda _exchange_manager, raw_trade: raw_trade,
            ),
        ):
            await repo.fetch_trades_paginated(
                ["ETH/USDT"],
                existing_config_symbols=set(),
                exchange_name="binance",
                account_id="acc-1",
                exchange_config_id="cfg-1",
                exchange_config_name="cfg-name",
                symbol_since_ms={"BTC/USDT": 1_700_000_000_000},
            )

        updater.fetch_trades.assert_awaited_once_with(
            ["ETH/USDT"],
            exhaust_history=True,
        )


class TestFetchTradesPaginatedMixedFullAndIncremental:
    @pytest.mark.asyncio
    async def test_mixed_symbols_use_separate_fetch_calls(self):
        exchange_manager = _allow_all_symbols(mock.MagicMock())
        exchange_manager.exchange.get_option_value.return_value = False
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.side_effect = [
            [{"id": "btc-trade", "symbol": "BTC/USDT"}],
            [{"id": "eth-trade", "symbol": "ETH/USDT"}],
        ]
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                side_effect=lambda _exchange_manager, raw_trade: raw_trade,
            ),
        ):
            result = await repo.fetch_trades_paginated(
                ["BTC/USDT", "ETH/USDT"],
                existing_config_symbols=set(),
                exchange_name="binance",
                account_id="acc-1",
                exchange_config_id="cfg-1",
                exchange_config_name="cfg-name",
                symbol_since_ms={"BTC/USDT": 1_700_000_000_000},
            )

        assert updater.fetch_trades.await_args_list == [
            mock.call(["ETH/USDT"], exhaust_history=True),
            mock.call(["BTC/USDT"], since=1_700_000_000_000, exhaust_history=True),
        ]
        assert {trade["id"] for trade in result} == {"btc-trade", "eth-trade"}


class TestFetchTradesPaginatedIncrementalAccountWide:
    @pytest.mark.asyncio
    async def test_account_wide_incremental_uses_min_since(self):
        exchange_manager = _allow_all_symbols(mock.MagicMock())
        exchange_manager.exchange.get_option_value.return_value = True
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.return_value = [
            {"id": "trade-1", "symbol": "ALGO/USDC", "timestamp": 1700000000.0},
            {"id": "trade-2", "symbol": "SOL/USDC", "timestamp": 1700000001.0},
        ]
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                side_effect=lambda _exchange_manager, raw_trade: raw_trade,
            ),
        ):
            result = await repo.fetch_trades_paginated(
                ["ALGO/USDC", "SOL/USDC"],
                existing_config_symbols=set(),
                exchange_name="kraken",
                account_id="acc-1",
                exchange_config_id="cfg-1",
                exchange_config_name="cfg-name",
                symbol_since_ms={
                    "ALGO/USDC": 1_700_000_000_100,
                    "SOL/USDC": 1_700_000_000_000,
                },
            )

        updater.fetch_trades.assert_awaited_once_with(
            [],
            since=1_700_000_000_000,
            exhaust_history=True,
        )
        assert len(result) == 2


class TestFetchTradesPaginatedMixedAccountWide:
    @pytest.mark.asyncio
    async def test_account_wide_incremental_plus_per_symbol_full_for_new_symbol(self):
        exchange_manager = _allow_all_symbols(mock.MagicMock())
        exchange_manager.exchange.get_option_value.return_value = True
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.side_effect = [
            [{"id": "trade-1", "symbol": "ALGO/USDC", "timestamp": 1700000000.0}],
            [{"id": "trade-2", "symbol": "SOL/USDC", "timestamp": 1700000001.0}],
        ]
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                side_effect=lambda _exchange_manager, raw_trade: raw_trade,
            ),
        ):
            result = await repo.fetch_trades_paginated(
                ["ALGO/USDC", "SOL/USDC"],
                existing_config_symbols=set(),
                exchange_name="kraken",
                account_id="acc-1",
                exchange_config_id="cfg-1",
                exchange_config_name="cfg-name",
                symbol_since_ms={"ALGO/USDC": 1_700_000_000_000},
            )

        assert updater.fetch_trades.await_args_list == [
            mock.call([], since=1_700_000_000_000, exhaust_history=True),
            mock.call(["SOL/USDC"], exhaust_history=True),
        ]
        assert {trade["id"] for trade in result} == {"trade-1", "trade-2"}


class TestFetchTradesPaginatedIncrementalEmptyMap:
    @pytest.mark.asyncio
    async def test_none_symbol_since_ms_matches_full_fetch(self):
        exchange_manager = _allow_all_symbols(mock.MagicMock())
        exchange_manager.exchange.get_option_value.return_value = False
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.return_value = [
            {"id": "trade-1", "timestamp": 1700000000.0, "symbol": "BTC/USDT"},
        ]
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                side_effect=lambda _exchange_manager, raw_trade: raw_trade,
            ),
        ):
            result = await repo.fetch_trades_paginated(
                ["BTC/USDT"],
                existing_config_symbols=set(),
                exchange_name="binance",
                account_id="acc-1",
                exchange_config_id="cfg-1",
                exchange_config_name="cfg-name",
                symbol_since_ms=None,
            )

        updater.fetch_trades.assert_awaited_once_with(
            ["BTC/USDT"],
            exhaust_history=True,
        )
        assert len(result) == 1


class TestFetchTradesPaginatedIncrementalDedupesAcrossGroups:
    @pytest.mark.asyncio
    async def test_duplicate_trade_across_groups_is_deduped(self):
        exchange_manager = _allow_all_symbols(mock.MagicMock())
        exchange_manager.exchange.get_option_value.return_value = False
        repo = _make_repo(exchange_manager)
        duplicate_trade = {
            trading_enums.ExchangeConstantsOrderColumns.ID.value: "trade-1",
            trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_TRADE_ID.value: "trade-1",
            trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "BTC/USDT",
            trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: 1700000000.0,
        }
        updater = mock.AsyncMock()
        updater.fetch_trades.side_effect = [
            [duplicate_trade],
            [duplicate_trade],
        ]
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                side_effect=lambda _exchange_manager, raw_trade: raw_trade,
            ),
        ):
            result = await repo.fetch_trades_paginated(
                ["BTC/USDT", "ETH/USDT"],
                existing_config_symbols=set(),
                exchange_name="binance",
                account_id="acc-1",
                exchange_config_id="cfg-1",
                exchange_config_name="cfg-name",
                symbol_since_ms={"BTC/USDT": 1_700_000_000_000},
            )

        assert len(result) == 1


class TestFetchTradesPaginatedIncrementalPerSymbolDifferentSince:
    @pytest.mark.asyncio
    async def test_incremental_symbols_with_different_since_get_separate_calls(self):
        exchange_manager = _allow_all_symbols(mock.MagicMock())
        exchange_manager.exchange.get_option_value.return_value = False
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.side_effect = [
            [{"id": "btc-trade", "symbol": "BTC/USDT"}],
            [{"id": "eth-trade", "symbol": "ETH/USDT"}],
        ]
        with (
            mock.patch.object(repo, "_get_trades_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                side_effect=lambda _exchange_manager, raw_trade: raw_trade,
            ),
        ):
            await repo.fetch_trades_paginated(
                ["BTC/USDT", "ETH/USDT"],
                existing_config_symbols=set(),
                exchange_name="binance",
                account_id="acc-1",
                exchange_config_id="cfg-1",
                exchange_config_name="cfg-name",
                symbol_since_ms={
                    "BTC/USDT": 1_700_000_000_100,
                    "ETH/USDT": 1_700_000_000_000,
                },
            )

        assert updater.fetch_trades.await_args_list == [
            mock.call(["BTC/USDT"], since=1_700_000_000_100, exhaust_history=True),
            mock.call(["ETH/USDT"], since=1_700_000_000_000, exhaust_history=True),
        ]
