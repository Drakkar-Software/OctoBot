import contextlib
import decimal
import time

import mock
import pytest

import octobot_commons.logging as commons_logging
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools

pytestmark = pytest.mark.asyncio

PENDING_STATUS = trading_enums.OrderStatus.PENDING_CREATION.value
OPEN_STATUS = trading_enums.OrderStatus.OPEN.value
SYMBOL = "SOL/USDC"
EXCHANGE_ORDER_ID = "coinbase-order-sol-1"


def _raw_order_dict(status: str) -> dict:
    return {
        trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: EXCHANGE_ORDER_ID,
        trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
        trading_enums.ExchangeConstantsOrderColumns.STATUS.value: status,
        trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.MARKET.value,
        trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
        trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: 1.0,
        trading_enums.ExchangeConstantsOrderColumns.PRICE.value: 100.0,
        trading_enums.ExchangeConstantsOrderColumns.FILLED.value: 0.0,
        trading_enums.ExchangeConstantsOrderColumns.REMAINING.value: 1.0,
        trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: time.time(),
    }


def _pending_order() -> mock.Mock:
    exchange_manager = mock.Mock(exchange_name="coinbase")
    order = mock.Mock(
        exchange_order_id=EXCHANGE_ORDER_ID,
        symbol=SYMBOL,
        order_type=trading_enums.TradeOrderType.MARKET,
        status=trading_enums.OrderStatus.PENDING_CREATION,
        exchange_manager=exchange_manager,
        get_logger_name=mock.Mock(return_value="pending_order_logger"),
    )
    return order


@contextlib.contextmanager
def _fast_poll_settings():
    with mock.patch.object(trading_constants, "CREATED_ORDER_FORCED_UPDATE_PERIOD", 0.01):
        yield


class TestWaitForOtherStatus:

    async def test_returns_immediately_when_status_changes_on_first_poll(self):
        order = _pending_order()
        confirmed_order = mock.Mock()
        order.exchange_manager.exchange.get_order = mock.AsyncMock(
            return_value=_raw_order_dict(OPEN_STATUS)
        )
        with mock.patch.object(
            exchanges_test_tools, "_parse_order_dict", mock.Mock(return_value=confirmed_order)
        ) as parse_order_dict_mock:
            result = await exchanges_test_tools.wait_for_other_status(order, timeout=1)
        assert result is confirmed_order
        order.exchange_manager.exchange.get_order.assert_awaited_once()
        parse_order_dict_mock.assert_called_once()

    async def test_raises_timeout_error_when_get_order_always_returns_none(self):
        order = _pending_order()
        order.exchange_manager.exchange.get_order = mock.AsyncMock(return_value=None)
        order.exchange_manager.exchange.get_open_orders = mock.AsyncMock(return_value=[])
        with _fast_poll_settings(), pytest.raises(TimeoutError):
            await exchanges_test_tools.wait_for_other_status(order, timeout=0.05)

    async def test_logs_at_iterations_five_and_ten(self):
        order = _pending_order()
        order.exchange_manager.exchange.get_order = mock.AsyncMock(return_value=None)
        order.exchange_manager.exchange.get_open_orders = mock.AsyncMock(return_value=[])
        order_logger = mock.Mock()
        with _fast_poll_settings(), mock.patch.object(
            commons_logging, "get_logger", mock.Mock(return_value=order_logger)
        ):
            with pytest.raises(TimeoutError):
                await exchanges_test_tools.wait_for_other_status(order, timeout=0.2)
        poll_log_messages = [
            call.args[0]
            for call in order_logger.info.mock_calls
            if call.args and "pending order status poll" in call.args[0]
        ]
        assert len(poll_log_messages) >= 2
        assert "pending order status poll 5" in poll_log_messages[0]
        assert "pending order status poll 10" in poll_log_messages[1]

    async def test_does_not_log_on_iterations_one_through_four(self):
        order = _pending_order()
        poll_count = {"count": 0}

        async def get_order_side_effect(*args, **kwargs):
            poll_count["count"] += 1
            if poll_count["count"] >= 5:
                return _raw_order_dict(OPEN_STATUS)
            return None

        order.exchange_manager.exchange.get_order = mock.AsyncMock(side_effect=get_order_side_effect)
        confirmed_order = mock.Mock()
        order_logger = mock.Mock()
        with _fast_poll_settings(), mock.patch.object(
            commons_logging, "get_logger", mock.Mock(return_value=order_logger)
        ), mock.patch.object(
            exchanges_test_tools, "_parse_order_dict", mock.Mock(return_value=confirmed_order)
        ):
            await exchanges_test_tools.wait_for_other_status(order, timeout=1)
        poll_log_messages = [
            call.args[0]
            for call in order_logger.info.mock_calls
            if call.args and "pending order status poll" in call.args[0]
        ]
        assert poll_log_messages == []

    async def test_returns_when_open_orders_fallback_finds_order(self):
        order = _pending_order()
        order.exchange_manager.exchange.get_order = mock.AsyncMock(return_value=None)
        order.exchange_manager.exchange.get_open_orders = mock.AsyncMock(
            return_value=[_raw_order_dict(OPEN_STATUS)]
        )
        confirmed_order = mock.Mock()
        with _fast_poll_settings(), mock.patch.object(
            exchanges_test_tools, "_parse_order_dict", mock.Mock(return_value=confirmed_order)
        ):
            result = await exchanges_test_tools.wait_for_other_status(order, timeout=1)
        assert result is confirmed_order
        order.exchange_manager.exchange.get_open_orders.assert_awaited()


class TestCreateOrderDeferConfirmation:

    async def test_defer_true_returns_pending_order_without_waiting(self):
        exchange_manager = mock.Mock(exchange_name="coinbase")
        pending_order = mock.Mock(status=trading_enums.OrderStatus.PENDING_CREATION)
        order_dict = {
            trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
            trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.MARKET.value,
            trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
            trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: 1.0,
            trading_enums.ExchangeConstantsOrderColumns.PRICE.value: 100.0,
            trading_enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value: False,
        }
        exchange_manager.exchange.create_order = mock.AsyncMock(return_value=_raw_order_dict(PENDING_STATUS))
        exchange_manager.exchange.get_order_additional_params = mock.Mock(return_value={})
        with mock.patch.object(
            exchanges_test_tools, "_parse_order_dict", mock.Mock(side_effect=[pending_order, pending_order])
        ), mock.patch.object(
            exchanges_test_tools, "wait_for_other_status", mock.AsyncMock()
        ) as wait_for_other_status_mock:
            result = await exchanges_test_tools._create_order(
                exchange_manager,
                order_dict,
                order_creation_timeout=60,
                price_by_symbol={SYMBOL: 100.0},
                defer_status_confirmation=True,
            )
        assert result is pending_order
        wait_for_other_status_mock.assert_not_called()

    async def test_defer_false_blocks_until_confirmation(self):
        exchange_manager = mock.Mock(exchange_name="coinbase")
        pending_order = mock.Mock(status=trading_enums.OrderStatus.PENDING_CREATION)
        confirmed_order = mock.Mock(status=trading_enums.OrderStatus.OPEN)
        order_dict = {
            trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
            trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.MARKET.value,
            trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
            trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: 1.0,
            trading_enums.ExchangeConstantsOrderColumns.PRICE.value: 100.0,
            trading_enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value: False,
        }
        exchange_manager.exchange.create_order = mock.AsyncMock(return_value=_raw_order_dict(PENDING_STATUS))
        exchange_manager.exchange.get_order_additional_params = mock.Mock(return_value={})
        with mock.patch.object(
            exchanges_test_tools, "_parse_order_dict", mock.Mock(side_effect=[pending_order, pending_order])
        ), mock.patch.object(
            exchanges_test_tools, "wait_for_other_status", mock.AsyncMock(return_value=confirmed_order)
        ) as wait_for_other_status_mock:
            result = await exchanges_test_tools._create_order(
                exchange_manager,
                order_dict,
                order_creation_timeout=60,
                price_by_symbol={SYMBOL: 100.0},
                defer_status_confirmation=False,
            )
        assert result is confirmed_order
        wait_for_other_status_mock.assert_awaited_once_with(pending_order, 60)


class TestConfirmOrderStatus:

    async def test_delegates_to_wait_for_other_status_with_same_timeout(self):
        order = _pending_order()
        confirmed_order = mock.Mock()
        with mock.patch.object(
            exchanges_test_tools, "wait_for_other_status", mock.AsyncMock(return_value=confirmed_order)
        ) as wait_for_other_status_mock:
            result = await exchanges_test_tools.confirm_order_status(order, timeout=42)
        assert result is confirmed_order
        wait_for_other_status_mock.assert_awaited_once_with(order, 42)
