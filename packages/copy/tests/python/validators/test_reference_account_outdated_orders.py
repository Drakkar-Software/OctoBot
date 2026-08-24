#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
import decimal
import time

import mock
import pytest

import octobot_commons.timestamp_util as timestamp_util
import octobot_protocol.models as protocol_models

import octobot_copy.constants as copy_constants
import octobot_copy.errors as copy_errors
import octobot_copy.validators.reference_account_outdated_orders as reference_account_outdated_orders_module

_THRESHOLD = decimal.Decimal(str(copy_constants.OUTDATED_ORDER_PRICE_MAX_THRESHOLD))
_BTC_USDC = "BTC/USDC"


def _open_limit_order(
    *,
    order_id: str = "reference-order-id",
    symbol: str = _BTC_USDC,
    price: float,
    side: protocol_models.Side = protocol_models.Side.SELL,
    trigger_above: bool | None = True,
    status: protocol_models.OrderStatus = protocol_models.OrderStatus.OPEN,
) -> protocol_models.Order:
    return protocol_models.Order(
        id=order_id,
        symbol=symbol,
        price=price,
        quantity=0.001,
        filled=0.0,
        exchange_id="ex",
        side=side,
        type=protocol_models.OrderType.LIMIT,
        trigger_above=trigger_above,
        reduce_only=False,
        is_active=True,
        status=status,
        created_at=timestamp_util.utc_datetime_from_timestamp(time.time()),
    )


def _copied_account(
    *,
    orders: list[protocol_models.Order] | None = None,
) -> protocol_models.CopiedAccount:
    return protocol_models.CopiedAccount(
        version=copy_constants.COPIED_ACCOUNT_VERSION,
        updated_at=1710000000.0,
        copied_assets=[],
        orders=orders,
    )


class TestResolveOrderTriggerAbove:
    def test_uses_explicit_trigger_above_when_set(self):
        order = _open_limit_order(price=95000.0, side=protocol_models.Side.SELL, trigger_above=False)
        assert reference_account_outdated_orders_module.resolve_order_trigger_above(order) is False

    def test_infers_true_for_sell_when_trigger_above_missing(self):
        order = _open_limit_order(price=95000.0, side=protocol_models.Side.SELL, trigger_above=None)
        assert reference_account_outdated_orders_module.resolve_order_trigger_above(order) is True

    def test_infers_false_for_buy_when_trigger_above_missing(self):
        order = _open_limit_order(price=95000.0, side=protocol_models.Side.BUY, trigger_above=None)
        assert reference_account_outdated_orders_module.resolve_order_trigger_above(order) is False


class TestIsOrderImpossibleAtMarketPrice:
    def test_sell_stale_when_far_below_market(self):
        order = _open_limit_order(price=67326.0, trigger_above=True)
        assert reference_account_outdated_orders_module.is_order_impossible_at_market_price(
            order,
            decimal.Decimal("110000"),
            _THRESHOLD,
        )

    def test_sell_not_stale_when_near_market(self):
        order = _open_limit_order(price=107000.0, trigger_above=True)
        assert not reference_account_outdated_orders_module.is_order_impossible_at_market_price(
            order,
            decimal.Decimal("110000"),
            _THRESHOLD,
        )

    def test_buy_stale_when_far_above_market(self):
        order = _open_limit_order(price=113500.0, side=protocol_models.Side.BUY, trigger_above=False)
        assert reference_account_outdated_orders_module.is_order_impossible_at_market_price(
            order,
            decimal.Decimal("110000"),
            _THRESHOLD,
        )

    def test_buy_not_stale_when_near_market(self):
        order = _open_limit_order(price=113000.0, side=protocol_models.Side.BUY, trigger_above=False)
        assert not reference_account_outdated_orders_module.is_order_impossible_at_market_price(
            order,
            decimal.Decimal("110000"),
            _THRESHOLD,
        )


class TestEnsureReferenceAccountNotOutdated:
    @pytest.mark.asyncio
    async def test_raises_when_order_is_impossible(self):
        reference_account = _copied_account(
            orders=[_open_limit_order(price=67326.0, trigger_above=True)],
        )
        exchange_interface = mock.Mock()
        exchange_interface.market.get_potentially_outdated_price = mock.Mock(
            return_value=(decimal.Decimal("110000"), False),
        )
        with pytest.raises(copy_errors.OutdatedReferenceAccountError):
            await reference_account_outdated_orders_module.ensure_reference_account_not_outdated(
                reference_account,
                exchange_interface,
            )

    @pytest.mark.asyncio
    async def test_no_op_when_no_orders(self):
        exchange_interface = mock.Mock()
        await reference_account_outdated_orders_module.ensure_reference_account_not_outdated(
            _copied_account(orders=[]),
            exchange_interface,
        )
        exchange_interface.market.get_potentially_outdated_price.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignores_non_open_orders(self):
        reference_account = _copied_account(
            orders=[
                _open_limit_order(
                    price=67326.0,
                    trigger_above=True,
                    status=protocol_models.OrderStatus.FILLED,
                )
            ],
        )
        exchange_interface = mock.Mock()
        await reference_account_outdated_orders_module.ensure_reference_account_not_outdated(
            reference_account,
            exchange_interface,
        )
        exchange_interface.market.get_potentially_outdated_price.assert_not_called()

    @pytest.mark.asyncio
    async def test_passes_when_orders_are_near_market(self):
        reference_account = _copied_account(
            orders=[_open_limit_order(price=107000.0, trigger_above=True)],
        )
        exchange_interface = mock.Mock()
        exchange_interface.market.get_potentially_outdated_price = mock.Mock(
            return_value=(decimal.Decimal("110000"), False),
        )
        await reference_account_outdated_orders_module.ensure_reference_account_not_outdated(
            reference_account,
            exchange_interface,
        )
