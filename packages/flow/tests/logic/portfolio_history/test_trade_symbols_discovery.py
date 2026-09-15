import datetime

import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.util.exchange_util as exchange_util_module

import octobot_flow.logic.portfolio_history.trade_symbols_discovery as trade_symbols_discovery_module


_TEST_TIMESTAMP = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)


def _make_account(assets: dict[str, float]) -> protocol_models.Account:
    detailed_assets = [
        protocol_models.DetailedAsset(symbol=symbol, total=amount, available=amount)
        for symbol, amount in assets.items()
    ]
    exchange_account = protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        remote_account_id="remote1",
        exchange_config_ids=["cfg1"],
    )
    return protocol_models.Account(
        id="acc1",
        name="Test",
        is_simulated=False,
        created_at=_TEST_TIMESTAMP,
        updated_at=_TEST_TIMESTAMP,
        specifics=protocol_models.AccountSpecifics(actual_instance=exchange_account),
        assets=[
            protocol_models.DetailedAssetsForTradingType(
                trading_type=protocol_models.TradingType.SPOT,
                assets=detailed_assets,
            )
        ],
    )


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


def _make_transaction(asset: str) -> protocol_models.Transaction:
    return protocol_models.Transaction(
        id=f"tx-{asset}",
        timestamp=_TEST_TIMESTAMP,
        asset=asset,
        amount=1.0,
        type=protocol_models.TransactionType.BLOCKCHAIN_DEPOSIT,
    )


def _exchange_manager_with_markets(valid_currencies: set[str]):
    exchange_manager = mock.MagicMock()

    def get_associated_symbol(_exchange_manager, currency, reference_market):
        if currency in valid_currencies:
            return f"{currency}/{reference_market}", False
        return None, False

    exchange_manager.symbol_exists.side_effect = lambda symbol: "/" in symbol
    return exchange_manager, get_associated_symbol


class TestDiscoverTradeSymbolsSeeds:
    def test_returns_sorted_union_of_seed_symbols(self):
        exchange_manager, get_associated_symbol = _exchange_manager_with_markets(set())
        with mock.patch.object(
            exchange_util_module,
            "get_associated_symbol",
            side_effect=get_associated_symbol,
        ):
            result = trade_symbols_discovery_module.discover_trade_symbols(
                exchange_manager,
                seed_symbols=["SOL/USDC", "BTC/USDC"],
                account=_make_account({}),
                account_trading=None,
                fresh_transactions=[],
                reference_market="USDC",
            )
        assert result == ["BTC/USDC", "SOL/USDC"]


class TestDiscoverTradeSymbolsPersisted:
    def test_includes_symbols_from_persisted_trades(self):
        exchange_manager, get_associated_symbol = _exchange_manager_with_markets(set())
        account_trading = protocol_models.AccountTrading(
            trades=[_make_trade("ALGO/USDC")],
            updated_at=_TEST_TIMESTAMP,
        )
        with mock.patch.object(
            exchange_util_module,
            "get_associated_symbol",
            side_effect=get_associated_symbol,
        ):
            result = trade_symbols_discovery_module.discover_trade_symbols(
                exchange_manager,
                seed_symbols=[],
                account=_make_account({}),
                account_trading=account_trading,
                fresh_transactions=[],
                reference_market="USDC",
            )
        assert "ALGO/USDC" in result

    def test_maps_persisted_transaction_currency_to_market_pair(self):
        exchange_manager, get_associated_symbol = _exchange_manager_with_markets({"ALGO"})
        account_trading = protocol_models.AccountTrading(
            transactions=[_make_transaction("ALGO")],
            updated_at=_TEST_TIMESTAMP,
        )
        with mock.patch.object(
            exchange_util_module,
            "get_associated_symbol",
            side_effect=get_associated_symbol,
        ):
            result = trade_symbols_discovery_module.discover_trade_symbols(
                exchange_manager,
                seed_symbols=[],
                account=_make_account({}),
                account_trading=account_trading,
                fresh_transactions=[],
                reference_market="USDC",
            )
        assert "ALGO/USDC" in result


class TestDiscoverTradeSymbolsFreshTransactions:
    def test_includes_fresh_deposit_currency_with_valid_market(self):
        exchange_manager, get_associated_symbol = _exchange_manager_with_markets({"ETH"})
        fresh_deposit = {
            trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value: "ETH",
        }
        with mock.patch.object(
            exchange_util_module,
            "get_associated_symbol",
            side_effect=get_associated_symbol,
        ):
            result = trade_symbols_discovery_module.discover_trade_symbols(
                exchange_manager,
                seed_symbols=[],
                account=_make_account({}),
                account_trading=None,
                fresh_transactions=[fresh_deposit],
                reference_market="USDC",
            )
        assert "ETH/USDC" in result

    def test_skips_reference_market_deposit_currency(self):
        exchange_manager, get_associated_symbol = _exchange_manager_with_markets(set())
        fresh_deposit = {
            trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value: "USDC",
        }
        with mock.patch.object(
            exchange_util_module,
            "get_associated_symbol",
            side_effect=get_associated_symbol,
        ):
            result = trade_symbols_discovery_module.discover_trade_symbols(
                exchange_manager,
                seed_symbols=[],
                account=_make_account({}),
                account_trading=None,
                fresh_transactions=[fresh_deposit],
                reference_market="USDC",
            )
        assert "USDC/USDC" not in result


class TestDiscoverTradeSymbolsPortfolio:
    def test_includes_meaningful_holding_with_valid_market(self):
        exchange_manager, get_associated_symbol = _exchange_manager_with_markets({"ALGO"})
        with mock.patch.object(
            exchange_util_module,
            "get_associated_symbol",
            side_effect=get_associated_symbol,
        ):
            result = trade_symbols_discovery_module.discover_trade_symbols(
                exchange_manager,
                seed_symbols=[],
                account=_make_account({"ALGO": 100.0, "USDC": 402.0}),
                account_trading=None,
                fresh_transactions=[],
                reference_market="USDC",
            )
        assert "ALGO/USDC" in result

    def test_skips_dust_holding_below_threshold(self):
        exchange_manager, get_associated_symbol = _exchange_manager_with_markets({"BTC"})
        with mock.patch.object(
            exchange_util_module,
            "get_associated_symbol",
            side_effect=get_associated_symbol,
        ):
            result = trade_symbols_discovery_module.discover_trade_symbols(
                exchange_manager,
                seed_symbols=[],
                account=_make_account({"BTC": 1e-8}),
                account_trading=None,
                fresh_transactions=[],
                reference_market="USDC",
            )
        assert "BTC/USDC" not in result

    def test_skips_holding_when_no_market_exists(self):
        exchange_manager, get_associated_symbol = _exchange_manager_with_markets(set())
        exchange_manager.symbol_exists.side_effect = lambda symbol: False
        with mock.patch.object(
            exchange_util_module,
            "get_associated_symbol",
            side_effect=get_associated_symbol,
        ):
            result = trade_symbols_discovery_module.discover_trade_symbols(
                exchange_manager,
                seed_symbols=[],
                account=_make_account({"UNKNOWN": 100.0}),
                account_trading=None,
                fresh_transactions=[],
                reference_market="USDC",
            )
        assert not any("UNKNOWN" in symbol for symbol in result)

    def test_skips_usd_like_and_reference_market_assets(self):
        exchange_manager, get_associated_symbol = _exchange_manager_with_markets(set())
        with mock.patch.object(
            exchange_util_module,
            "get_associated_symbol",
            side_effect=get_associated_symbol,
        ):
            result = trade_symbols_discovery_module.discover_trade_symbols(
                exchange_manager,
                seed_symbols=["SOL/USDC"],
                account=_make_account({"USDC": 402.0}),
                account_trading=None,
                fresh_transactions=[],
                reference_market="USDC",
            )
        assert result == ["SOL/USDC"]

    def test_excludes_pair_when_quote_not_held(self):
        exchange_manager, get_associated_symbol = _exchange_manager_with_markets({"ALGO"})
        with mock.patch.object(
            exchange_util_module,
            "get_associated_symbol",
            side_effect=get_associated_symbol,
        ):
            result = trade_symbols_discovery_module.discover_trade_symbols(
                exchange_manager,
                seed_symbols=[],
                account=_make_account({"ALGO": 100.0, "USDC": 402.0}),
                account_trading=None,
                fresh_transactions=[],
                reference_market="USDC",
            )
        assert "ALGO/USDC" in result
        assert "ALGO/USDT" not in result

    def test_uses_reference_market_pair_only_per_held_asset(self):
        exchange_manager = mock.MagicMock()
        exchange_manager.symbol_exists.side_effect = lambda symbol: symbol in {
            "DOT/USDC",
            "BTC/USDC",
            "ETH/USDC",
            "EUR/USDC",
        }
        with mock.patch.object(
            exchange_util_module,
            "get_associated_symbol",
            side_effect=lambda _exchange_manager, currency, reference_market: (None, False),
        ):
            result = trade_symbols_discovery_module.discover_trade_symbols(
                exchange_manager,
                seed_symbols=[],
                account=_make_account({
                    "DOT": 1.0,
                    "BTC": 0.001,
                    "ETH": 0.01,
                    "EUR": 10.0,
                    "USDC": 402.0,
                }),
                account_trading=None,
                fresh_transactions=[],
                reference_market="USDC",
            )
        assert "DOT/USDC" in result
        assert "BTC/USDC" in result
        assert "ETH/USDC" in result
        assert "EUR/USDC" in result
        assert "DOT/BTC" not in result
        assert "DOT/EUR" not in result
        assert "DOT/ETH" not in result

    def test_includes_only_reference_market_pair_per_held_base(self):
        exchange_manager = mock.MagicMock()
        exchange_manager.symbol_exists.side_effect = lambda symbol: symbol in {"ALGO/USDC", "ALGO/USDT"}
        with mock.patch.object(
            exchange_util_module,
            "get_associated_symbol",
            side_effect=lambda _exchange_manager, currency, reference_market: (None, False),
        ):
            result = trade_symbols_discovery_module.discover_trade_symbols(
                exchange_manager,
                seed_symbols=[],
                account=_make_account({"ALGO": 100.0, "USDC": 402.0, "USDT": 50.0}),
                account_trading=None,
                fresh_transactions=[],
                reference_market="USDC",
            )
        assert "ALGO/USDC" in result
        assert "ALGO/USDT" not in result


class TestDiscoverTradeSymbolsDedup:
    def test_deduplicates_across_all_sources(self):
        exchange_manager, get_associated_symbol = _exchange_manager_with_markets({"ALGO"})
        account_trading = protocol_models.AccountTrading(
            trades=[_make_trade("ALGO/USDC")],
            updated_at=_TEST_TIMESTAMP,
        )
        with mock.patch.object(
            exchange_util_module,
            "get_associated_symbol",
            side_effect=get_associated_symbol,
        ):
            result = trade_symbols_discovery_module.discover_trade_symbols(
                exchange_manager,
                seed_symbols=["ALGO/USDC"],
                account=_make_account({"ALGO": 100.0}),
                account_trading=account_trading,
                fresh_transactions=[],
                reference_market="USDC",
            )
        assert result.count("ALGO/USDC") == 1
