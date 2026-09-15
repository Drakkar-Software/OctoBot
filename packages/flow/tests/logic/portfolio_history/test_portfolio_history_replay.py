import datetime
import decimal

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models
import octobot_trading.personal_data.portfolios.history.history_from_trades_and_transaction_builder as history_builder_module


DAY_1_TS = 1700000000.0
DAY_2_TS = DAY_1_TS + 86400
DAY_3_TS = DAY_2_TS + 86400


def _make_trade(
    trade_id: str,
    symbol: str,
    side: protocol_models.Side,
    quantity: float,
    price: float,
    executed_at: datetime.datetime,
) -> protocol_models.Trade:
    return protocol_models.Trade(
        id=trade_id,
        trade_id=trade_id,
        type=protocol_models.OrderType.LIMIT,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        status=protocol_models.OrderStatus.FILLED,
        executed_at=executed_at,
    )


def _latest_portfolio() -> dict[str, dict[str, decimal.Decimal]]:
    return {
        "USDC": {
            commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("402"),
            commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("402"),
        },
        "ALGO": {
            commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("100"),
            commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("100"),
        },
        "KNC": {
            commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("50"),
            commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("50"),
        },
        "SOL": {
            commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("2"),
            commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("2"),
        },
    }


def _all_pair_trades() -> list[protocol_models.Trade]:
    return [
        _make_trade(
            "sol-buy",
            "SOL/USDC",
            protocol_models.Side.BUY,
            quantity=2.0,
            price=50.0,
            executed_at=datetime.datetime.fromtimestamp(DAY_3_TS + 3600, tz=datetime.timezone.utc),
        ),
        _make_trade(
            "knc-buy",
            "KNC/USDC",
            protocol_models.Side.BUY,
            quantity=50.0,
            price=2.0,
            executed_at=datetime.datetime.fromtimestamp(DAY_2_TS + 3600, tz=datetime.timezone.utc),
        ),
        _make_trade(
            "algo-buy",
            "ALGO/USDC",
            protocol_models.Side.BUY,
            quantity=100.0,
            price=2.07,
            executed_at=datetime.datetime.fromtimestamp(DAY_1_TS + 3600, tz=datetime.timezone.utc),
        ),
    ]


def _sell_without_buy_trades() -> list[protocol_models.Trade]:
    return [
        _make_trade(
            "btc-sell",
            "BTC/USDC",
            protocol_models.Side.SELL,
            quantity=1.0,
            price=609.0,
            executed_at=datetime.datetime.fromtimestamp(DAY_2_TS + 3600, tz=datetime.timezone.utc),
        ),
    ]


def _usdc_holdings_by_day(
    trades: list[protocol_models.Trade],
    *,
    latest_portfolio: dict[str, dict[str, decimal.Decimal]] | None = None,
) -> dict[float, decimal.Decimal]:
    daily_holdings = history_builder_module.build_historical_holdings(
        latest_portfolio or _latest_portfolio(),
        trades,
        [],
    )
    usdc_by_day: dict[float, decimal.Decimal] = {}
    for day_timestamp, holdings in daily_holdings.items():
        usdc_amounts = holdings.get("USDC", {})
        usdc_by_day[day_timestamp] = usdc_amounts.get(
            commons_constants.PORTFOLIO_TOTAL,
            decimal.Decimal(0),
        )
    return usdc_by_day


class TestMultiPairReplayUsdcNonNegative:
    def test_usdc_non_negative_when_all_pair_trades_present(self):
        usdc_by_day = _usdc_holdings_by_day(_all_pair_trades())
        assert usdc_by_day
        assert all(usdc_total >= 0 for usdc_total in usdc_by_day.values())

    def test_usdc_goes_negative_when_pair_trades_missing(self):
        latest_portfolio = {
            "USDC": {
                commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("402"),
                commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("402"),
            },
            "BTC": {
                commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("0"),
                commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("0"),
            },
        }
        usdc_by_day = _usdc_holdings_by_day(
            _sell_without_buy_trades(),
            latest_portfolio=latest_portfolio,
        )
        assert any(usdc_total < 0 for usdc_total in usdc_by_day.values())


class TestBingxMultiPageBalancedTradesReplay:
    def test_holdings_non_negative_when_balanced_buy_sell_pairs_present(self):
        latest_portfolio = {
            "USDT": {
                commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("7"),
                commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("7"),
            },
            "TRX": {
                commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("1.656"),
                commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("1.656"),
            },
        }
        trades = [
            _make_trade(
                "sol-buy-1",
                "SOL/USDT",
                protocol_models.Side.BUY,
                quantity=36.5,
                price=50.0,
                executed_at=datetime.datetime.fromtimestamp(DAY_1_TS + 3600, tz=datetime.timezone.utc),
            ),
            _make_trade(
                "sol-sell-1",
                "SOL/USDT",
                protocol_models.Side.SELL,
                quantity=36.5,
                price=55.0,
                executed_at=datetime.datetime.fromtimestamp(DAY_2_TS + 3600, tz=datetime.timezone.utc),
            ),
            _make_trade(
                "trx-buy-1",
                "TRX/USDT",
                protocol_models.Side.BUY,
                quantity=500.0,
                price=0.1,
                executed_at=datetime.datetime.fromtimestamp(DAY_1_TS + 7200, tz=datetime.timezone.utc),
            ),
            _make_trade(
                "trx-sell-1",
                "TRX/USDT",
                protocol_models.Side.SELL,
                quantity=498.344,
                price=0.11,
                executed_at=datetime.datetime.fromtimestamp(DAY_2_TS + 7200, tz=datetime.timezone.utc),
            ),
            _make_trade(
                "trx-buy-2",
                "TRX/USDT",
                protocol_models.Side.BUY,
                quantity=200.0,
                price=0.1,
                executed_at=datetime.datetime.fromtimestamp(DAY_3_TS + 3600, tz=datetime.timezone.utc),
            ),
            _make_trade(
                "trx-sell-2",
                "TRX/USDT",
                protocol_models.Side.SELL,
                quantity=200.0,
                price=0.12,
                executed_at=datetime.datetime.fromtimestamp(DAY_3_TS + 7200, tz=datetime.timezone.utc),
            ),
        ]
        daily_holdings = history_builder_module.build_historical_holdings(
            latest_portfolio,
            trades,
            [],
        )
        assert daily_holdings
        for day_holdings in daily_holdings.values():
            for asset_symbol in ("SOL", "TRX"):
                asset_amounts = day_holdings.get(asset_symbol, {})
                total = asset_amounts.get(
                    commons_constants.PORTFOLIO_TOTAL,
                    decimal.Decimal(0),
                )
                assert total >= 0
