import decimal
import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_trading.enums as enums
import octobot_trading.exchanges.connectors.ccxt.ccxt_adapter as ccxt_adapter_module
import octobot_trading.personal_data.transactions.protocol as transactions_protocol
import octobot_trading.personal_data.portfolios.history.history_from_trades_and_transaction_builder as history_builder


DAY_SECONDS = commons_constants.DAYS_TO_SECONDS
TOTAL = commons_constants.PORTFOLIO_TOTAL


def _ccxt_adapter() -> ccxt_adapter_module.CCXTAdapter:
    return ccxt_adapter_module.CCXTAdapter(mock.Mock())


def _ccxt_transaction(**overrides) -> dict:
    transaction = {
        enums.ExchangeConstantsTransactionColumns.ID.value: "tx-internal-1",
        enums.ExchangeConstantsTransactionColumns.TXID.value: "tx-blockchain-1",
        enums.ExchangeConstantsTransactionColumns.TIMESTAMP.value: 1_700_002_000,
        enums.ExchangeConstantsTransactionColumns.CURRENCY.value: "SOL",
        enums.ExchangeConstantsTransactionColumns.AMOUNT.value: 200,
        enums.ExchangeConstantsTransactionColumns.TYPE.value: "withdrawal",
        enums.ExchangeConstantsTransactionColumns.STATUS.value: "ok",
    }
    transaction.update(overrides)
    return transaction


class TestCcxtAdapterParseTransaction:
    def test_enforces_withdrawal_type_when_provided(self):
        adapter = _ccxt_adapter()

        parsed = adapter.parse_transaction(
            _ccxt_transaction(),
            transaction_type=enums.TransactionType.BLOCKCHAIN_WITHDRAWAL,
        )

        assert parsed[enums.ExchangeConstantsTransactionColumns.TYPE.value] == (
            enums.TransactionType.BLOCKCHAIN_WITHDRAWAL.value
        )
        assert parsed[enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == decimal.Decimal("200")

    def test_enforces_deposit_type_when_provided(self):
        adapter = _ccxt_adapter()

        parsed = adapter.parse_transaction(
            _ccxt_transaction(type="deposit"),
            transaction_type=enums.TransactionType.BLOCKCHAIN_DEPOSIT,
        )

        assert parsed[enums.ExchangeConstantsTransactionColumns.TYPE.value] == (
            enums.TransactionType.BLOCKCHAIN_DEPOSIT.value
        )

    def test_raises_when_transaction_type_not_provided(self):
        adapter = _ccxt_adapter()

        with pytest.raises(ValueError, match="transaction_type is required"):
            adapter.parse_transaction(_ccxt_transaction(type="withdrawal"))


class TestCcxtAdapterParseTransactions:
    def test_parses_each_transaction_through_parse_transaction(self):
        adapter = _ccxt_adapter()
        transactions = [
            _ccxt_transaction(txid="tx-1"),
            _ccxt_transaction(txid="tx-2", amount=50),
        ]

        parsed = adapter.parse_transactions(
            transactions,
            transaction_type=enums.TransactionType.BLOCKCHAIN_WITHDRAWAL,
        )

        assert len(parsed) == 2
        assert all(
            transaction[enums.ExchangeConstantsTransactionColumns.TYPE.value]
            == enums.TransactionType.BLOCKCHAIN_WITHDRAWAL.value
            for transaction in parsed
        )
        assert parsed[1][enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == decimal.Decimal("50")


class TestCcxtAdapterWithdrawalHistoryReplay:
    def test_enforced_withdrawal_replays_positive_holdings_before_withdraw(self):
        adapter = _ccxt_adapter()
        withdrawal_timestamp_ms = int((DAY_SECONDS * 4 + 200) * 1000)
        parsed = adapter.parse_transaction(
            _ccxt_transaction(timestamp=withdrawal_timestamp_ms),
            transaction_type=enums.TransactionType.BLOCKCHAIN_WITHDRAWAL,
        )
        protocol_transaction = transactions_protocol.to_protocol_transaction(parsed)
        portfolio = {
            "SOL": {
                TOTAL: decimal.Decimal("0"),
                commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("0"),
            }
        }

        historical_holdings = history_builder.build_historical_holdings(
            portfolio,
            [],
            [protocol_transaction],
        )

        day_before_withdraw = DAY_SECONDS * 3
        assert historical_holdings[day_before_withdraw]["SOL"][TOTAL] == decimal.Decimal("200")
