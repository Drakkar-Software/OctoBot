#  Drakkar-Software OctoBot-Flow

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

import octobot_flow.logic.exchange.simulator.simulated_order_fill_detector as simulated_order_fill_detector_module


def _open_order_storage_dict(
    exchange_id: str,
    *,
    price: float = 10000.0,
    symbol: str = "BTC/USDT",
    trigger_above: bool | None = None,
    side: str | None = None,
) -> dict:
    order_columns = trading_enums.ExchangeConstantsOrderColumns
    inner_order = {
        order_columns.EXCHANGE_ID.value: exchange_id,
        order_columns.ID.value: exchange_id,
        order_columns.SYMBOL.value: symbol,
        order_columns.PRICE.value: price,
    }
    if trigger_above is not None:
        inner_order[order_columns.TRIGGER_ABOVE.value] = trigger_above
    if side is not None:
        inner_order[order_columns.SIDE.value] = side
    return {
        trading_constants.STORAGE_ORIGIN_VALUE: inner_order,
    }


class TestIsSimulatedOrderFilled:
    def test_trigger_above_false_fills_when_market_at_or_below_order_price(self):
        assert simulated_order_fill_detector_module.is_simulated_order_filled(
            order_price=10000.0,
            market_price=9000.0,
            trigger_above=False,
        )

    def test_trigger_above_false_stays_open_when_market_above_order_price(self):
        assert not simulated_order_fill_detector_module.is_simulated_order_filled(
            order_price=10000.0,
            market_price=11000.0,
            trigger_above=False,
        )

    def test_trigger_above_true_fills_when_market_at_or_above_order_price(self):
        assert simulated_order_fill_detector_module.is_simulated_order_filled(
            order_price=10000.0,
            market_price=11000.0,
            trigger_above=True,
        )

    def test_trigger_above_true_stays_open_when_market_below_order_price(self):
        assert not simulated_order_fill_detector_module.is_simulated_order_filled(
            order_price=10000.0,
            market_price=9000.0,
            trigger_above=True,
        )


class TestResolveSimulatedOpenOrders:
    def test_drops_filled_orders_and_keeps_open_ones(self):
        open_orders = [
            _open_order_storage_dict("filled-order", price=10000.0, trigger_above=False),
            _open_order_storage_dict("open-order", price=8000.0, trigger_above=False),
        ]
        still_open_orders = simulated_order_fill_detector_module.resolve_simulated_open_orders(
            open_orders,
            {"BTC/USDT": 9000.0},
        )
        remaining_exchange_ids = {
            order[trading_constants.STORAGE_ORIGIN_VALUE][
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value
            ]
            for order in still_open_orders
        }
        assert remaining_exchange_ids == {"open-order"}

    def test_keeps_order_open_when_ticker_missing(self):
        open_orders = [_open_order_storage_dict("order-1", trigger_above=False)]
        still_open_orders = simulated_order_fill_detector_module.resolve_simulated_open_orders(
            open_orders,
            {},
        )
        assert len(still_open_orders) == 1

    def test_infers_trigger_above_from_sell_side_when_missing(self):
        open_orders = [
            _open_order_storage_dict(
                "filled-sell",
                price=10000.0,
                side=trading_enums.TradeOrderSide.SELL.value,
            ),
        ]
        still_open_orders = simulated_order_fill_detector_module.resolve_simulated_open_orders(
            open_orders,
            {"BTC/USDT": 11000.0},
        )
        assert still_open_orders == []

    def test_infers_trigger_above_from_buy_side_when_missing(self):
        open_orders = [
            _open_order_storage_dict(
                "filled-buy",
                price=10000.0,
                side=trading_enums.TradeOrderSide.BUY.value,
            ),
        ]
        still_open_orders = simulated_order_fill_detector_module.resolve_simulated_open_orders(
            open_orders,
            {"BTC/USDT": 9000.0},
        )
        assert still_open_orders == []


class TestSymbolsFromOpenOrders:
    def test_returns_unique_sorted_symbols(self):
        open_orders = [
            _open_order_storage_dict("order-1", symbol="ETH/USDT"),
            _open_order_storage_dict("order-2", symbol="BTC/USDT"),
            _open_order_storage_dict("order-3", symbol="BTC/USDT"),
        ]
        assert simulated_order_fill_detector_module.symbols_from_open_orders(open_orders) == [
            "BTC/USDT",
            "ETH/USDT",
        ]
