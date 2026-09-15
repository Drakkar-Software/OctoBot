import datetime
import decimal
import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models
import octobot_trading.enums as enums
import octobot_trading.personal_data.portfolios.history.history_from_trades_and_transaction_builder as builder
import octobot_trading.personal_data.trades.protocol as trades_protocol


TOTAL = commons_constants.PORTFOLIO_TOTAL
AVAILABLE = commons_constants.PORTFOLIO_AVAILABLE
DAY_SECONDS = commons_constants.DAYS_TO_SECONDS


def _make_portfolio(assets: dict[str, decimal.Decimal]) -> dict[str, dict[str, decimal.Decimal]]:
    return {
        asset: {TOTAL: amount, AVAILABLE: amount}
        for asset, amount in assets.items()
    }


def _timestamp_to_datetime(timestamp: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)


def _make_protocol_trade(
    trade_id: str,
    symbol: str,
    side: protocol_models.Side,
    quantity: float,
    price: float,
    executed_at: datetime.datetime,
    fee: protocol_models.Fee | None = None,
) -> protocol_models.Trade:
    return protocol_models.Trade(
        id=trade_id,
        trade_id=trade_id,
        type=protocol_models.OrderType.LIMIT,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        fee=fee,
        status=protocol_models.OrderStatus.FILLED,
        executed_at=executed_at,
    )


def _make_protocol_transaction(
    tx_id: str,
    asset: str,
    amount: float,
    tx_type: protocol_models.TransactionType,
    timestamp: datetime.datetime,
) -> protocol_models.Transaction:
    return protocol_models.Transaction(
        id=tx_id,
        timestamp=timestamp,
        asset=asset,
        amount=amount,
        type=tx_type,
    )


class TestBuildHistoricalHoldingsEmptyEvents:
    def test_no_trades_no_transactions(self):
        portfolio = _make_portfolio({"BTC": decimal.Decimal("1")})
        result = builder.build_historical_holdings(portfolio, [], [])
        assert result == {}

    def test_empty_portfolio_empty_events(self):
        result = builder.build_historical_holdings({}, [], [])
        assert result == {}


class TestBuildHistoricalHoldingsBuySell:
    def test_single_buy_trade(self):
        # Latest: 1 BTC, 0 USDT.
        # Trade at day 1 end: BUY 0.5 BTC @ 40000 USDT.
        # Before this trade: 0.5 BTC, 20000 USDT.
        day_1_end = DAY_SECONDS + 3600
        portfolio = _make_portfolio({
            "BTC": decimal.Decimal("1"),
            "USDT": decimal.Decimal("0"),
        })
        trade = _make_protocol_trade(
            "trade-1", "BTC/USDT", protocol_models.Side.BUY,
            0.5, 40000, _timestamp_to_datetime(day_1_end),
        )
        result = builder.build_historical_holdings(portfolio, [trade], [])

        day_1_start = DAY_SECONDS
        assert day_1_start in result
        assert result[day_1_start]["BTC"][TOTAL] == decimal.Decimal("1")
        assert result[day_1_start]["USDT"][TOTAL] == decimal.Decimal("0")

        day_0_start = 0.0
        assert day_0_start in result
        assert result[day_0_start]["BTC"][TOTAL] == decimal.Decimal("0.5")
        assert result[day_0_start]["USDT"][TOTAL] == decimal.Decimal("20000")

    def test_single_sell_trade(self):
        day_2_ts = DAY_SECONDS * 2 + 100
        portfolio = _make_portfolio({
            "BTC": decimal.Decimal("0.5"),
            "USDT": decimal.Decimal("20000"),
        })
        trade = _make_protocol_trade(
            "trade-1", "BTC/USDT", protocol_models.Side.SELL,
            0.5, 40000, _timestamp_to_datetime(day_2_ts),
        )
        result = builder.build_historical_holdings(portfolio, [trade], [])

        day_2_start = DAY_SECONDS * 2
        assert result[day_2_start]["BTC"][TOTAL] == decimal.Decimal("0.5")

        day_1_start = DAY_SECONDS
        assert result[day_1_start]["BTC"][TOTAL] == decimal.Decimal("1")
        assert result[day_1_start]["USDT"][TOTAL] == decimal.Decimal("0")


class TestBuildHistoricalHoldingsDepositWithdrawal:
    def test_deposit(self):
        day_3_ts = DAY_SECONDS * 3 + 500
        portfolio = _make_portfolio({"BTC": decimal.Decimal("2")})
        deposit = _make_protocol_transaction(
            "deposit-1", "BTC", 1,
            protocol_models.TransactionType.BLOCKCHAIN_DEPOSIT,
            _timestamp_to_datetime(day_3_ts),
        )
        result = builder.build_historical_holdings(portfolio, [], [deposit])

        day_3_start = DAY_SECONDS * 3
        assert result[day_3_start]["BTC"][TOTAL] == decimal.Decimal("2")

        day_2_start = DAY_SECONDS * 2
        assert result[day_2_start]["BTC"][TOTAL] == decimal.Decimal("1")

    def test_withdrawal(self):
        day_4_ts = DAY_SECONDS * 4 + 200
        portfolio = _make_portfolio({"BTC": decimal.Decimal("1")})
        withdrawal = _make_protocol_transaction(
            "withdrawal-1", "BTC", 0.5,
            protocol_models.TransactionType.BLOCKCHAIN_WITHDRAWAL,
            _timestamp_to_datetime(day_4_ts),
        )
        result = builder.build_historical_holdings(portfolio, [], [withdrawal])

        day_4_start = DAY_SECONDS * 4
        assert result[day_4_start]["BTC"][TOTAL] == decimal.Decimal("1")

        day_3_start = DAY_SECONDS * 3
        assert result[day_3_start]["BTC"][TOTAL] == decimal.Decimal("1.5")


class TestBuildHistoricalHoldingsMixedTimeline:
    def test_trades_and_deposits_across_days(self):
        day_5_ts = DAY_SECONDS * 5 + 100
        day_3_ts = DAY_SECONDS * 3 + 100

        portfolio = _make_portfolio({
            "BTC": decimal.Decimal("1.5"),
            "USDT": decimal.Decimal("10000"),
        })
        trade = _make_protocol_trade(
            "trade-1", "BTC/USDT", protocol_models.Side.BUY,
            0.5, 40000, _timestamp_to_datetime(day_5_ts),
        )
        deposit = _make_protocol_transaction(
            "deposit-1", "BTC", 1,
            protocol_models.TransactionType.BLOCKCHAIN_DEPOSIT,
            _timestamp_to_datetime(day_3_ts),
        )

        result = builder.build_historical_holdings(portfolio, [trade], [deposit])

        assert result[DAY_SECONDS * 5]["BTC"][TOTAL] == decimal.Decimal("1.5")
        assert result[DAY_SECONDS * 3]["BTC"][TOTAL] == decimal.Decimal("1")
        assert result[DAY_SECONDS * 2]["BTC"][TOTAL] == decimal.Decimal("0")


class TestBuildHistoricalHoldingsWithFees:
    def test_buy_with_base_fee(self):
        day_1_ts = DAY_SECONDS + 100
        portfolio = _make_portfolio({
            "BTC": decimal.Decimal("0.999"),
            "USDT": decimal.Decimal("0"),
        })
        trade = _make_protocol_trade(
            "trade-1", "BTC/USDT", protocol_models.Side.BUY,
            1, 40000, _timestamp_to_datetime(day_1_ts),
            fee=protocol_models.Fee(currency="BTC", amount=0.001),
        )
        result = builder.build_historical_holdings(portfolio, [trade], [])

        assert result[0.0]["BTC"][TOTAL] == decimal.Decimal("0")
        assert result[0.0]["USDT"][TOTAL] == decimal.Decimal("40000")

    def test_sell_with_quote_fee(self):
        day_1_ts = DAY_SECONDS + 100
        portfolio = _make_portfolio({
            "BTC": decimal.Decimal("0"),
            "USDT": decimal.Decimal("39990"),
        })
        trade = _make_protocol_trade(
            "trade-1", "BTC/USDT", protocol_models.Side.SELL,
            1, 40000, _timestamp_to_datetime(day_1_ts),
            fee=protocol_models.Fee(currency="USDT", amount=10),
        )
        result = builder.build_historical_holdings(portfolio, [trade], [])

        assert result[0.0]["BTC"][TOTAL] == decimal.Decimal("1")
        assert result[0.0]["USDT"][TOTAL] == decimal.Decimal("0")


class TestBuildHistoricalHoldingsFeeTransactions:
    def test_funding_fee_reversed(self):
        day_2_ts = DAY_SECONDS * 2 + 100
        portfolio = _make_portfolio({"USDT": decimal.Decimal("100")})
        fee_tx = _make_protocol_transaction(
            "fee-1", "USDT", 5,
            protocol_models.TransactionType.FUNDING_FEE,
            _timestamp_to_datetime(day_2_ts),
        )
        result = builder.build_historical_holdings(portfolio, [], [fee_tx])

        assert result[DAY_SECONDS]["USDT"][TOTAL] == decimal.Decimal("105")

    def test_trading_fee_reversed(self):
        day_2_ts = DAY_SECONDS * 2 + 100
        portfolio = _make_portfolio({"USDT": decimal.Decimal("100")})
        fee_tx = _make_protocol_transaction(
            "fee-1", "USDT", 5,
            protocol_models.TransactionType.TRADING_FEE,
            _timestamp_to_datetime(day_2_ts),
        )
        result = builder.build_historical_holdings(portfolio, [], [fee_tx])

        assert result[DAY_SECONDS]["USDT"][TOTAL] == decimal.Decimal("105")


class TestBuildHistoricalHoldingsDayBoundaries:
    def test_multiple_events_same_day_single_snapshot(self):
        day_1_early = DAY_SECONDS + 100
        day_1_late = DAY_SECONDS + 50000
        portfolio = _make_portfolio({
            "BTC": decimal.Decimal("2"),
            "USDT": decimal.Decimal("0"),
        })
        trade_1 = _make_protocol_trade(
            "trade-1", "BTC/USDT", protocol_models.Side.BUY,
            1, 40000, _timestamp_to_datetime(day_1_late),
        )
        trade_2 = _make_protocol_trade(
            "trade-2", "BTC/USDT", protocol_models.Side.BUY,
            1, 40000, _timestamp_to_datetime(day_1_early),
        )
        result = builder.build_historical_holdings(portfolio, [trade_1, trade_2], [])

        day_1_start = DAY_SECONDS
        assert day_1_start in result
        assert 0.0 in result
        assert result[0.0]["BTC"][TOTAL] == decimal.Decimal("0")
        assert result[0.0]["USDT"][TOTAL] == decimal.Decimal("80000")


class TestBuildHistoricalHoldingsEventErrorHandling:
    def test_continues_after_unsupported_event(self):
        day_1_ts = DAY_SECONDS + 100
        day_2_ts = DAY_SECONDS * 2 + 100
        portfolio = _make_portfolio({
            "BTC": decimal.Decimal("1"),
            "USDT": decimal.Decimal("0"),
        })
        trade = _make_protocol_trade(
            "trade-1", "BTC/USDT", protocol_models.Side.BUY,
            0.5, 40000, _timestamp_to_datetime(day_1_ts),
        )
        unsupported_event = object()

        trade_only_result = builder.build_historical_holdings(portfolio, [trade], [])
        with mock.patch.object(
            builder,
            "_build_sorted_events",
            return_value=[(day_2_ts, unsupported_event), (day_1_ts, trade)],
        ):
            mixed_result = builder.build_historical_holdings(portfolio, [trade], [])

        assert mixed_result[DAY_SECONDS] == trade_only_result[DAY_SECONDS]
        assert mixed_result[0.0] == trade_only_result[0.0]
        assert mixed_result[DAY_SECONDS * 2]["BTC"][TOTAL] == decimal.Decimal("1")
        assert mixed_result[DAY_SECONDS * 2]["USDT"][TOTAL] == decimal.Decimal("0")

    def test_logs_exception_when_event_processing_fails(self):
        day_1_ts = DAY_SECONDS + 100
        portfolio = _make_portfolio({
            "BTC": decimal.Decimal("1"),
            "USDT": decimal.Decimal("0"),
        })
        trade = _make_protocol_trade(
            "trade-1", "BTC/USDT", protocol_models.Side.BUY,
            0.5, 40000, _timestamp_to_datetime(day_1_ts),
        )
        logger_mock = mock.MagicMock()
        with mock.patch.object(
            builder,
            "_build_sorted_events",
            return_value=[(day_1_ts, trade), (day_1_ts + 50, object())],
        ):
            with mock.patch(
                "octobot_trading.personal_data.portfolios.history.history_from_trades_and_transaction_builder.logging_module.get_logger",
                return_value=logger_mock,
            ):
                builder.build_historical_holdings(
                    portfolio,
                    [trade],
                    [],
                )

        logger_mock.exception.assert_called_once()
        exception_args = logger_mock.exception.call_args[0]
        assert isinstance(exception_args[0], ValueError)


class TestComputeReverseDelta:
    def test_raises_on_unsupported_event(self):
        with pytest.raises(ValueError, match="Unexpected event type"):
            builder._compute_reverse_delta(object())


class TestUtcDayStart:
    def test_midnight(self):
        assert builder._utc_day_start(DAY_SECONDS) == DAY_SECONDS

    def test_mid_day(self):
        assert builder._utc_day_start(DAY_SECONDS + DAY_SECONDS // 2) == DAY_SECONDS

    def test_just_before_midnight(self):
        assert builder._utc_day_start(DAY_SECONDS - 1) == 0.0

    def test_zero(self):
        assert builder._utc_day_start(0.0) == 0.0
