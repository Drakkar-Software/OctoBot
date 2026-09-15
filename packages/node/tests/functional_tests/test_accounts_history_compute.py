#  Drakkar-Software OctoBot-Node

"""
Functional tests for on-the-fly portfolio history computation.

Each test seeds persisted Account (current holdings), AccountTrading (trades /
transactions), and exchange price caches, then calls
compute_portfolio_historical_values_from_latest_portfolio_trades_and_transactions.

The compute path reverse-replays trades and transactions from the latest
portfolio to reconstruct past daily holdings, then values each day using daily
prices (or latest tickers when daily prices are missing).
"""

import pytest

import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants

import octobot_node.protocol.accounts_history as accounts_history_module
from tests.functional_tests.util import accounts_history_test_util as accounts_history_test_util


@pytest.mark.asyncio
class TestComputeHistoryFunctionalSimulated:
    """End-to-end history compute with seeded sync providers and persisted caches."""

    async def test_single_buy_trade_produces_two_day_history(self, tmp_path):
        """
        Scenario: account holds 1 BTC and 50000 USDT now.
        One historical buy of 1 BTC at 30000 USDT on day 1.
        Daily price cache has BTC/USDT = 30000 on day 1 and 50000 on day 2.
        Expected: day 1 portfolio had 0 BTC + 80000 USDT, day 2 has 1 BTC + 50000 USDT.
        """
        # Latest portfolio anchor: what the account holds today.
        account = accounts_history_test_util.make_account("a1", {"BTC": 1.0, "USDT": 50000.0})
        exchange_config = accounts_history_test_util.make_exchange_config()
        # Single BUY on day 1; reverse replay will subtract 1 BTC and credit 30000 USDT.
        trade = accounts_history_test_util.make_protocol_trade(
            "t1",
            "BTC/USDT",
            protocol_models.Side.BUY,
            quantity=1.0,
            price=30000.0,
            executed_at=accounts_history_test_util.BUY_TIME,
        )

        buy_day_str = str(
            accounts_history_test_util.utc_day_start(accounts_history_test_util.BUY_TIME.timestamp())
        )
        buy_day_start = int(buy_day_str)
        prior_day_str = str(buy_day_start - 86400)
        next_day_str = str(
            accounts_history_test_util.utc_day_start(accounts_history_test_util.DAY_2_TS)
        )
        data_root = str(tmp_path)

        # Prior day and day 1 close price 30000; day 2 close price 50000 (current-day valuation).
        await accounts_history_test_util.write_daily_prices_cache(
            data_root,
            "binance",
            "spot",
            False,
            {"BTC/USDT": {prior_day_str: 30000.0, buy_day_str: 30000.0, next_day_str: 50000.0}},
        )
        await accounts_history_test_util.write_latest_tickers_cache(
            data_root,
            "binance",
            "spot",
            False,
            {"BTC/USDT": 50000.0},
        )

        with accounts_history_test_util.accounts_history_test_environment(tmp_path) as (
            account_provider,
            trading_provider,
        ):
            accounts_history_test_util.seed_exchange_config(
                account_provider,
                accounts_history_test_util.TEST_USER_ID,
                exchange_config,
            )
            accounts_history_test_util.seed_account(
                account_provider,
                accounts_history_test_util.TEST_USER_ID,
                account,
            )
            accounts_history_test_util.seed_trading_state(
                trading_provider,
                accounts_history_test_util.TEST_USER_ID,
                "a1",
                trades=[trade],
            )
            with accounts_history_test_util.with_current_time(accounts_history_test_util.DAY_2_TS):
                result = await accounts_history_module.compute_portfolio_historical_values_from_latest_portfolio_trades_and_transactions(
                    accounts_history_test_util.TEST_USER_ID,
                    "a1",
                    data_root=data_root,
                )

        assert result.version == sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION
        assert result.history is not None
        assert result.history.unit == "USDT"
        assert len(result.history.values) == 3

        day_values = {
            int(history_value.timestamp.timestamp()): history_value.total
            for history_value in result.history.values
        }
        prior_day_start = buy_day_start - 86400
        next_day_start = int(next_day_str)
        assert prior_day_start in day_values
        assert buy_day_start in day_values
        assert next_day_start in day_values
        # Before the buy: 0 BTC + 80000 USDT (50000 + 1 * 30000), valued at 30000/BTC → 80000.
        assert day_values[prior_day_start] == pytest.approx(80000.0)
        # After the buy on day 1: 1 BTC + 50000 USDT, valued at 30000/BTC → 80000.
        assert day_values[buy_day_start] == pytest.approx(80000.0)
        # Day 2 forward-filled holdings repriced at 50000/BTC → 100000.
        assert day_values[next_day_start] == pytest.approx(100000.0)

        history_by_day = {
            int(history_value.timestamp.timestamp()): history_value
            for history_value in result.history.values
        }
        prior_day = history_by_day[prior_day_start]
        buy_day = history_by_day[buy_day_start]
        assert prior_day.assets is not None and len(prior_day.assets) > 0
        prior_spot_assets = prior_day.assets[0].assets or []
        prior_assets_by_symbol = {asset.symbol: asset for asset in prior_spot_assets}
        assert "USDT" in prior_assets_by_symbol
        assert prior_assets_by_symbol["USDT"].holdings == pytest.approx(80000.0)
        assert prior_assets_by_symbol["USDT"].value == pytest.approx(80000.0)
        assert "BTC" not in prior_assets_by_symbol

        buy_spot_assets = buy_day.assets[0].assets or []
        buy_assets_by_symbol = {asset.symbol: asset for asset in buy_spot_assets}
        assert buy_assets_by_symbol["BTC"].holdings == pytest.approx(1.0)
        assert buy_assets_by_symbol["BTC"].value == pytest.approx(30000.0)
        assert buy_assets_by_symbol["USDT"].holdings == pytest.approx(50000.0)
        assert buy_assets_by_symbol["USDT"].value == pytest.approx(50000.0)

    async def test_deposit_and_trade_produce_coherent_history(self, tmp_path):
        """
        Scenario: account holds 2 BTC and 20000 USDT now.
        Day 1: bought 1 BTC at 30000 USDT.
        Day 2: deposited 1 BTC.
        Daily price for BTC/USDT: day 1 = 30000, day 2 = 35000.
        """
        # Latest: 2 BTC + 20000 USDT.
        account = accounts_history_test_util.make_account("a1", {"BTC": 2.0, "USDT": 20000.0})
        exchange_config = accounts_history_test_util.make_exchange_config()
        # Day 1 BUY: reverse removes 1 BTC and adds 30000 USDT → 1 BTC + 20000 USDT.
        trade = accounts_history_test_util.make_protocol_trade(
            "t1",
            "BTC/USDT",
            protocol_models.Side.BUY,
            quantity=1.0,
            price=30000.0,
            executed_at=accounts_history_test_util.BUY_TIME,
        )
        # Day 2 deposit: reverse removes 1 BTC → 1 BTC + 20000 USDT before deposit.
        deposit = accounts_history_test_util.make_protocol_transaction(
            "tx1",
            "BTC",
            1.0,
            protocol_models.TransactionType.BLOCKCHAIN_DEPOSIT,
            accounts_history_test_util.DEPOSIT_TIME,
        )

        buy_day_str = str(
            accounts_history_test_util.utc_day_start(accounts_history_test_util.BUY_TIME.timestamp())
        )
        buy_day_start = int(buy_day_str)
        prior_day_str = str(buy_day_start - 86400)
        deposit_day_str = str(
            accounts_history_test_util.utc_day_start(accounts_history_test_util.DEPOSIT_TIME.timestamp())
        )
        data_root = str(tmp_path)

        await accounts_history_test_util.write_daily_prices_cache(
            data_root,
            "binance",
            "spot",
            False,
            {"BTC/USDT": {prior_day_str: 30000.0, buy_day_str: 30000.0, deposit_day_str: 35000.0}},
        )
        await accounts_history_test_util.write_latest_tickers_cache(
            data_root,
            "binance",
            "spot",
            False,
            {"BTC/USDT": 35000.0},
        )

        with accounts_history_test_util.accounts_history_test_environment(tmp_path) as (
            account_provider,
            trading_provider,
        ):
            accounts_history_test_util.seed_exchange_config(
                account_provider,
                accounts_history_test_util.TEST_USER_ID,
                exchange_config,
            )
            accounts_history_test_util.seed_account(
                account_provider,
                accounts_history_test_util.TEST_USER_ID,
                account,
            )
            accounts_history_test_util.seed_trading_state(
                trading_provider,
                accounts_history_test_util.TEST_USER_ID,
                "a1",
                trades=[trade],
                transactions=[deposit],
            )
            with accounts_history_test_util.with_current_time(
                accounts_history_test_util.DEPOSIT_TIME.timestamp(),
            ):
                result = await accounts_history_module.compute_portfolio_historical_values_from_latest_portfolio_trades_and_transactions(
                    accounts_history_test_util.TEST_USER_ID,
                    "a1",
                    data_root=data_root,
                )

        assert result.history is not None
        assert len(result.history.values) == 3

        day_values = {
            int(history_value.timestamp.timestamp()): history_value.total
            for history_value in result.history.values
        }
        deposit_day_start = accounts_history_test_util.utc_day_start(
            accounts_history_test_util.DEPOSIT_TIME.timestamp()
        )
        prior_day_start = buy_day_start - 86400
        assert deposit_day_start in day_values
        assert buy_day_start in day_values
        assert prior_day_start in day_values
        # After deposit on day 2: 2 BTC + 20000 USDT @ 35000 → 90000.
        assert day_values[deposit_day_start] == pytest.approx(90000.0)
        # After buy on day 1 (before deposit): 1 BTC + 20000 USDT @ 30000 → 50000.
        assert day_values[buy_day_start] == pytest.approx(50000.0)
        # Before buy: 0 BTC + 50000 USDT @ 30000 → 50000.
        assert day_values[prior_day_start] == pytest.approx(50000.0)

    async def test_no_account_returns_empty_state(self, tmp_path):
        """Missing account id must yield an empty history state, not an error."""
        with accounts_history_test_util.accounts_history_test_environment(tmp_path):
            result = await accounts_history_module.compute_portfolio_historical_values_from_latest_portfolio_trades_and_transactions(
                accounts_history_test_util.TEST_USER_ID,
                "missing",
            )

        assert result.history is None

    async def test_no_trading_data_returns_empty_state(self, tmp_path):
        """Account exists but AccountTrading was never seeded → no history to compute."""
        account = accounts_history_test_util.make_account("a1", {"BTC": 1.0})
        exchange_config = accounts_history_test_util.make_exchange_config()

        with accounts_history_test_util.accounts_history_test_environment(tmp_path) as (
            account_provider,
            _trading_provider,
        ):
            accounts_history_test_util.seed_exchange_config(
                account_provider,
                accounts_history_test_util.TEST_USER_ID,
                exchange_config,
            )
            accounts_history_test_util.seed_account(
                account_provider,
                accounts_history_test_util.TEST_USER_ID,
                account,
            )
            result = await accounts_history_module.compute_portfolio_historical_values_from_latest_portfolio_trades_and_transactions(
                accounts_history_test_util.TEST_USER_ID,
                "a1",
            )

        assert result.history is None

    async def test_ticker_fallback_when_no_daily_prices(self, tmp_path):
        """
        When daily price cache is empty, latest ticker is used for all days.

        Scenario: account holds 5 ETH and 1000 USDT now.
        One BUY of 5 ETH at 2000 USDT on day 1.
        Ticker fallback: ETH/USDT = 2500 for every day.
        """
        account = accounts_history_test_util.make_account("a1", {"ETH": 5.0, "USDT": 1000.0})
        exchange_config = accounts_history_test_util.make_exchange_config()
        trade = accounts_history_test_util.make_protocol_trade(
            "t1",
            "ETH/USDT",
            protocol_models.Side.BUY,
            quantity=5.0,
            price=2000.0,
            executed_at=accounts_history_test_util.BUY_TIME,
        )
        data_root = str(tmp_path)

        # Empty daily prices force valuation to use the latest ticker only.
        await accounts_history_test_util.write_daily_prices_cache(
            data_root,
            "binance",
            "spot",
            False,
            {},
        )
        await accounts_history_test_util.write_latest_tickers_cache(
            data_root,
            "binance",
            "spot",
            False,
            {"ETH/USDT": 2500.0},
        )

        with accounts_history_test_util.accounts_history_test_environment(tmp_path) as (
            account_provider,
            trading_provider,
        ):
            accounts_history_test_util.seed_exchange_config(
                account_provider,
                accounts_history_test_util.TEST_USER_ID,
                exchange_config,
            )
            accounts_history_test_util.seed_account(
                account_provider,
                accounts_history_test_util.TEST_USER_ID,
                account,
            )
            accounts_history_test_util.seed_trading_state(
                trading_provider,
                accounts_history_test_util.TEST_USER_ID,
                "a1",
                trades=[trade],
            )
            with accounts_history_test_util.with_current_time(accounts_history_test_util.DAY_2_TS):
                result = await accounts_history_module.compute_portfolio_historical_values_from_latest_portfolio_trades_and_transactions(
                    accounts_history_test_util.TEST_USER_ID,
                    "a1",
                    data_root=data_root,
                )

        assert result.history is not None
        assert len(result.history.values) == 3
        buy_day_start = accounts_history_test_util.utc_day_start(
            accounts_history_test_util.BUY_TIME.timestamp()
        )
        prior_day_start = buy_day_start - 86400
        day_values = {
            int(history_value.timestamp.timestamp()): history_value.total
            for history_value in result.history.values
        }
        # Before buy: 0 ETH + 11000 USDT (1000 + 5 * 2000), all in USDT → 11000.
        assert day_values[prior_day_start] == pytest.approx(11000.0)
        # After buy: 5 ETH + 1000 USDT @ 2500 ticker → 12500 + 1000 = 13500.
        assert day_values[buy_day_start] == pytest.approx(13500.0)
