#  Drakkar-Software OctoBot-Flow

import pytest

import octobot_flow.jobs.portfolio_history_job as portfolio_history_job_module
from tests.functionnal_tests.portfolio_history import portfolio_history_test_util as portfolio_history_test_util


@pytest.mark.asyncio
class TestPortfolioHistoryJobFunctional:
    async def test_collects_and_persists_trading_history(self, tmp_path):
        account_id = "functional-account-1"
        context = portfolio_history_test_util.build_portfolio_history_context(
            account_id=account_id,
            symbols=["BTC/USDT"],
        )
        exchange_manager = await portfolio_history_test_util.build_exchange_manager(
            raw_trades=[portfolio_history_test_util.sample_raw_trade()],
            deposits=[portfolio_history_test_util.sample_deposit()],
            withdrawals=[portfolio_history_test_util.sample_withdrawal()],
            daily_candles=portfolio_history_test_util.sample_daily_candles(close_price=40500.0),
        )

        with portfolio_history_test_util.portfolio_history_test_environment(
            tmp_path,
            exchange_manager_by_account_id={account_id: exchange_manager},
        ) as trading_provider:
            portfolio_history_test_util.seed_empty_account_trading(
                trading_provider,
                portfolio_history_test_util.TEST_WALLET_ID,
                account_id,
            )
            results = await portfolio_history_job_module.PortfolioHistoryJob(
                portfolio_history_test_util.TEST_WALLET_ID,
                [context],
                data_root=str(tmp_path),
            ).run()

            assert len(results) == 1
            result = results[0]
            assert result.account_id == account_id
            assert result.trades_count == 1
            assert result.transactions_count == 2
            assert not result.skipped
            assert result.error is None

            account_trading = portfolio_history_test_util.load_account_trading(
                portfolio_history_test_util.TEST_WALLET_ID,
                account_id,
            )
            trade_ids = {trade.trade_id for trade in account_trading.trades or []}
            transaction_ids = {transaction.id for transaction in account_trading.transactions or []}
            assert "functional-trade-1" in trade_ids
            assert "functional-deposit-1" in transaction_ids
            assert "functional-withdrawal-1" in transaction_ids

            daily_prices = await portfolio_history_test_util.load_daily_prices_from_root(
                str(tmp_path),
                "binanceus",
                "spot",
                False,
            )
            assert daily_prices["symbols"]["BTC/USDT"]["86400"] == 40500.0
            assert "ETH/USDT" in daily_prices["symbols"]

    async def test_two_accounts_both_persist(self, tmp_path):
        account_id_1 = "functional-account-1"
        account_id_2 = "functional-account-2"
        context_1 = portfolio_history_test_util.build_portfolio_history_context(
            account_id=account_id_1,
            symbols=["BTC/USDT"],
        )
        context_2 = portfolio_history_test_util.build_portfolio_history_context(
            account_id=account_id_2,
            symbols=["ETH/USDT"],
        )
        exchange_manager_1 = await portfolio_history_test_util.build_exchange_manager(
            raw_trades=[
                portfolio_history_test_util.sample_raw_trade(
                    trade_id="account-1-trade",
                    symbol="BTC/USDT",
                )
            ],
            deposits=[portfolio_history_test_util.sample_deposit(txid="account-1-deposit")],
            withdrawals=[portfolio_history_test_util.sample_withdrawal(txid="account-1-withdrawal")],
            daily_candles=portfolio_history_test_util.sample_daily_candles(close_price=41000.0),
        )
        exchange_manager_2 = await portfolio_history_test_util.build_exchange_manager(
            raw_trades=[
                portfolio_history_test_util.sample_raw_trade(
                    trade_id="account-2-trade",
                    symbol="ETH/USDT",
                )
            ],
            deposits=[portfolio_history_test_util.sample_deposit(txid="account-2-deposit", currency="ETH")],
            withdrawals=[portfolio_history_test_util.sample_withdrawal(txid="account-2-withdrawal", currency="USDT")],
            daily_candles=portfolio_history_test_util.sample_daily_candles(
                day_timestamp_ms=172800000,
                close_price=2500.0,
            ),
        )

        with portfolio_history_test_util.portfolio_history_test_environment(
            tmp_path,
            exchange_manager_by_account_id={
                account_id_1: exchange_manager_1,
                account_id_2: exchange_manager_2,
            },
        ) as trading_provider:
            portfolio_history_test_util.seed_empty_account_trading(
                trading_provider,
                portfolio_history_test_util.TEST_WALLET_ID,
                account_id_1,
            )
            portfolio_history_test_util.seed_empty_account_trading(
                trading_provider,
                portfolio_history_test_util.TEST_WALLET_ID,
                account_id_2,
            )
            results = await portfolio_history_job_module.PortfolioHistoryJob(
                portfolio_history_test_util.TEST_WALLET_ID,
                [context_1, context_2],
                data_root=str(tmp_path),
            ).run()

            assert len(results) == 2
            assert all(not result.skipped for result in results)
            assert {result.account_id for result in results} == {account_id_1, account_id_2}

            account_trading_1 = portfolio_history_test_util.load_account_trading(
                portfolio_history_test_util.TEST_WALLET_ID,
                account_id_1,
            )
            account_trading_2 = portfolio_history_test_util.load_account_trading(
                portfolio_history_test_util.TEST_WALLET_ID,
                account_id_2,
            )
            assert {trade.trade_id for trade in account_trading_1.trades or []} == {"account-1-trade"}
            assert {trade.trade_id for trade in account_trading_2.trades or []} == {"account-2-trade"}
            assert {transaction.id for transaction in account_trading_1.transactions or []} == {
                "account-1-deposit",
                "account-1-withdrawal",
            }
            assert {transaction.id for transaction in account_trading_2.transactions or []} == {
                "account-2-deposit",
                "account-2-withdrawal",
            }
