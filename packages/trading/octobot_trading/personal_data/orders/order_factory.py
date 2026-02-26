#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import decimal
import typing

import octobot_commons.logging as logging

import octobot_trading.personal_data as personal_data
import octobot_trading.enums as enums
import octobot_trading.constants as constants

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges


def create_order_from_raw(
    trader: "octobot_trading.exchanges.Trader",
    raw_order: dict,
) -> "personal_data.Order":
    _, order_type = personal_data.parse_order_type(raw_order)
    return create_order_from_type(trader, order_type)


def create_order_instance_from_raw(
    trader: "octobot_trading.exchanges.Trader",
    raw_order: dict,
    force_open_or_pending_creation: bool = False,
    has_just_been_created: bool = False,
) -> "personal_data.Order":
    try:
        order = create_order_from_raw(trader, raw_order)
        order.update_from_raw(raw_order)
        if has_just_been_created:
            order.register_broker_applied_if_enabled()
        if force_open_or_pending_creation \
                and order.status not in (enums.OrderStatus.OPEN, enums.OrderStatus.PENDING_CREATION):
            order.status = enums.OrderStatus.OPEN
        return order
    except Exception as err:
        # log unparsable order to fix it
        logging.get_logger(__name__).exception(
            err, True, f"Unexpected {err} ({err.__class__.__name__}) error when parsing row order {raw_order}"
        )
        raise


def create_order_from_type(
    trader: "octobot_trading.exchanges.Trader",
    order_type: enums.TraderOrderType,
    side: typing.Optional[enums.TradeOrderSide] = None,
) -> "personal_data.Order":
    if side is None:
        return personal_data.TraderOrderTypeClasses[order_type](trader)
    return personal_data.TraderOrderTypeClasses[order_type](trader, side=side)


def create_order_instance(
    trader: "octobot_trading.exchanges.Trader",
    order_type: enums.TraderOrderType,
    symbol: str,
    current_price: decimal.Decimal,
    quantity: decimal.Decimal,
    price: decimal.Decimal = constants.ZERO,
    stop_price: decimal.Decimal = constants.ZERO,
    status: enums.OrderStatus = enums.OrderStatus.OPEN,
    order_id: typing.Optional[str] = None,
    exchange_order_id: typing.Optional[str] = None,
    filled_price: decimal.Decimal = constants.ZERO,
    average_price: decimal.Decimal = constants.ZERO,
    quantity_filled: decimal.Decimal = constants.ZERO,
    total_cost: decimal.Decimal = constants.ZERO,
    timestamp: int = 0,
    side: typing.Optional[enums.TradeOrderSide] = None,
    trigger_above: typing.Optional[bool] = None,
    fees_currency_side: typing.Optional[str] = None,
    group: typing.Optional[str] = None,
    tag: typing.Optional[str] = None,
    reduce_only: typing.Optional[bool] = None,
    quantity_currency: typing.Optional[str] = None,
    close_position: bool = False,
    exchange_creation_params: typing.Optional[dict] = None,
    associated_entry_id: typing.Optional[str] = None,
    trailing_profile: typing.Optional["personal_data.TrailingProfile"] = None,
    is_active: typing.Optional[bool] = None,
    active_trigger_price: typing.Optional[decimal.Decimal] = None,
    active_trigger_above: typing.Optional[bool] = None,
    cancel_policy: typing.Optional["personal_data.OrderCancelPolicy"] = None,
) -> "personal_data.Order":
    order = create_order_from_type(trader, order_type, side=side)
    order.update(
        order_type=order_type,
        symbol=symbol,
        current_price=current_price,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
        order_id=trader.parse_order_id(order_id),
        exchange_order_id=exchange_order_id,
        timestamp=timestamp,
        status=status,
        filled_price=filled_price,
        average_price=average_price,
        quantity_filled=quantity_filled,
        fee=None,
        total_cost=total_cost,
        fees_currency_side=fees_currency_side,
        group=group,
        tag=tag,
        reduce_only=reduce_only,
        quantity_currency=quantity_currency,
        close_position=close_position,
        exchange_creation_params=exchange_creation_params,
        associated_entry_id=associated_entry_id,
        trigger_above=trigger_above,
        trailing_profile=trailing_profile,
        is_active=is_active,
        active_trigger=personal_data.create_order_price_trigger(order, active_trigger_price, active_trigger_above)
            if active_trigger_price else None,
        cancel_policy=cancel_policy,
    )
    return order


def create_order_from_dict(
    trader: "octobot_trading.exchanges.Trader",
    order_dict: dict,
) -> "personal_data.Order":
    """
    :param trader: the trader to associate the order to
    :param order_dict: a dict formatted as from order.to_dict()
    :return: the created order instance
    """
    _, order_type = personal_data.parse_order_type(order_dict)
    return create_order_instance(
        trader,
        order_type,
        order_dict[enums.ExchangeConstantsOrderColumns.SYMBOL.value],
        constants.ZERO,
        order_dict[enums.ExchangeConstantsOrderColumns.AMOUNT.value],
        price=order_dict[enums.ExchangeConstantsOrderColumns.PRICE.value],
        status=enums.OrderStatus(order_dict[enums.ExchangeConstantsOrderColumns.STATUS.value]),
        order_id=order_dict[enums.ExchangeConstantsOrderColumns.ID.value],
        exchange_order_id=order_dict.get(enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value),
        quantity_filled=order_dict[enums.ExchangeConstantsOrderColumns.FILLED.value],
        timestamp=order_dict[enums.ExchangeConstantsOrderColumns.TIMESTAMP.value],
        side=enums.TradeOrderSide(order_dict[enums.ExchangeConstantsOrderColumns.SIDE.value]),
        trigger_above=order_dict.get(enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value),
        tag=order_dict[enums.ExchangeConstantsOrderColumns.TAG.value],
        reduce_only=order_dict[enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value],
    )


async def create_order_from_order_storage_details(
    order_storage_details: dict,
    exchange_manager: "octobot_trading.exchanges.ExchangeManager",
    pending_groups: dict,
) -> "personal_data.Order":
    order = create_order_from_dict(
        exchange_manager.trader,
        order_storage_details[constants.STORAGE_ORIGIN_VALUE]
    )
    order.update_from_storage_order_details(order_storage_details)
    await personal_data.create_orders_storage_related_elements(
        order, order_storage_details, exchange_manager, pending_groups
    )
    return order


async def restore_chained_orders_from_storage_order_details(
    order: "personal_data.Order",
    order_details: dict,
    exchange_manager: "octobot_trading.exchanges.ExchangeManager",
    pending_groups: dict,
) -> None:
    chained_orders = order_details.get(enums.StoredOrdersAttr.CHAINED_ORDERS.value, None)
    if chained_orders:
        for chained_order in chained_orders:
            chained_order_inst = await create_order_from_order_storage_details(
                chained_order, exchange_manager, pending_groups
            )
            await chained_order_inst.set_as_chained_order(
                order,
                chained_order.get(enums.StoredOrdersAttr.HAS_BEEN_BUNDLED.value, False),
                chained_order.get(enums.StoredOrdersAttr.EXCHANGE_CREATION_PARAMS.value, {}),
                chained_order.get(enums.StoredOrdersAttr.UPDATE_WITH_TRIGGERING_ORDER_FEES.value, False),
                **chained_order.get(enums.StoredOrdersAttr.TRADER_CREATION_KWARGS.value, {}),
            )
            order.add_chained_order(chained_order_inst)
            logging.get_logger(order.get_logger_name()).debug(f"Restored chained order: {chained_order_inst}")
