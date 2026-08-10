#  Drakkar-Software OctoBot-Flow

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.util.exchange_data as exchange_data_module

import octobot_flow.entities


def _order_dict(exchange_id: str, *, filled: float = 0) -> dict:
    return {
        trading_constants.STORAGE_ORIGIN_VALUE: {
            trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: exchange_id,
            trading_enums.ExchangeConstantsOrderColumns.FILLED.value: filled,
        }
    }


def _exchange_data(open_orders: list[dict], portfolio: dict[str, dict]) -> exchange_data_module.ExchangeData:
    return exchange_data_module.ExchangeData(
        orders_details=exchange_data_module.OrdersDetails(open_orders=open_orders),
        portfolio_details=exchange_data_module.PortfolioDetails(content=portfolio),
    )


class TestGlobalViewRefreshedElementsConfirmedChange:
    def test_detects_order_disappearance(self):
        before = octobot_flow.entities.GlobalViewRefreshedElements(
            _exchange_data(
                [_order_dict("order-1"), _order_dict("order-2")],
                {"USDT": {"total": 100.0}},
            ),
        )
        after_exchange_data = _exchange_data(
            [_order_dict("order-2")],
            {"USDT": {"total": 100.0}},
        )
        assert before.confirmed_change(after_exchange_data) is True

    def test_no_change_when_orders_and_portfolio_match(self):
        orders = [_order_dict("order-1")]
        portfolio = {"USDT": {"total": 100.0}}
        before = octobot_flow.entities.GlobalViewRefreshedElements(
            _exchange_data(orders, portfolio),
        )
        after_exchange_data = _exchange_data(orders, portfolio)
        assert before.confirmed_change(after_exchange_data) is False
