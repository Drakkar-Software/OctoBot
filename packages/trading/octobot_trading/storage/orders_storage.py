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
#  License along with this library
import copy
import decimal
import time
import dataclasses

import octobot_commons.channels_name as channels_name
import octobot_commons.enums as commons_enums
import octobot_commons.databases as commons_databases
import octobot_commons.logging as commons_logging
import octobot_commons.authentication as authentication

import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.storage.abstract_storage as abstract_storage
import octobot_trading.storage.util as storage_util
import octobot_trading.exchanges as exchanges


class OrdersStorage(abstract_storage.AbstractStorage):
    LIVE_CHANNEL = channels_name.OctoBotTradingChannelsName.ORDERS_CHANNEL.value
    HISTORY_TABLE = commons_enums.DBTables.ORDERS.value
    HISTORICAL_OPEN_ORDERS_TABLE = commons_enums.DBTables.HISTORICAL_ORDERS_UPDATES.value
    ENABLE_HISTORICAL_ORDER_UPDATES_STORAGE = constants.ENABLE_HISTORICAL_ORDERS_UPDATES_STORAGE
    IS_MULTI_EXCHANGE_STORAGE = True   # set True when this storage is updating data from all other exchanges as well

    def __init__(self, exchange_manager, use_live_consumer_in_backtesting=None, is_historical=None):
        super().__init__(
            exchange_manager, plot_settings=None,
            use_live_consumer_in_backtesting=use_live_consumer_in_backtesting, is_historical=is_historical
        )
        self.startup_orders = {}

    def should_store_data(self):
        return (
            constants.ENABLE_SIMULATED_ORDERS_STORAGE or not self.exchange_manager.is_trader_simulated
        ) and not self.exchange_manager.is_backtesting

    async def on_start(self):
        await self._load_startup_orders()

    async def _live_callback(
        self,
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        order: dict,
        update_type: str,
        is_from_bot: bool,
    ):
        await self.trigger_debounced_update_auth_data(False)
        # only store the current snapshot of open orders when order updates are received
        if self.should_store_data():
            await self._update_history()
            if self.ENABLE_HISTORICAL_ORDER_UPDATES_STORAGE:
                await self._add_historical_open_orders(order, update_type)
            await self.trigger_debounced_flush()

    @abstract_storage.AbstractStorage.hard_reset_and_retry_if_necessary
    async def _update_history(self):
        await self._get_db().replace_all(
            self.HISTORY_TABLE,
            [
                _format_order(order, self.exchange_manager)
                for order in self.exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
            ],
            cache=False,
        )

    async def _add_historical_open_orders(self, order_dict: dict, update_type: str):
        update_time = time.time()
        await self._get_db().log(
            self.HISTORICAL_OPEN_ORDERS_TABLE,
            _format_order_update(self.exchange_manager, order_dict, update_type, update_time),
            cache=False,
        )

    async def _update_auth_data(self, _):
        authenticator = authentication.Authenticator.instance()

        orders_by_exchange = {
            exchange_manager.exchange_name: [
                _format_order(order, exchange_manager)
                for order in exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
            ]
            for exchange_manager in exchanges.Exchanges.instance().get_exchanges_managers_with_same_matrix_id(
                self.exchange_manager
            )
            if exchange_manager.exchange_personal_data.orders_manager
        }
        if authenticator.is_initialized():
            # also update when history is empty to reset trade history
            await authenticator.update_orders(orders_by_exchange)

    async def _store_history(self):
        await self._update_history()
        await self._get_db().flush()

    def _get_db(self):
        return commons_databases.RunDatabasesProvider.instance().get_orders_db(
            self.exchange_manager.bot_id,
            storage_util.get_account_type_suffix_from_exchange_manager(self.exchange_manager),
            self.exchange_manager.exchange_name,
        )

    async def get_historical_orders_updates(self):
        return copy.deepcopy(await self._get_db().all(self.HISTORICAL_OPEN_ORDERS_TABLE))

    async def get_startup_order_details(self, order_exchange__id):
        return self.startup_orders.get(order_exchange__id, None)

    async def _load_startup_orders(self):
        if self.should_store_data():
            self.startup_orders = {
                _get_startup_order_key(order): from_order_document(order)
                for order in copy.deepcopy(await self._get_db().all(self.HISTORY_TABLE))
                if order    # skip empty order details (error when serializing)
            }
        else:
            self.startup_orders = {}

    def get_startup_virtual_orders_details_from_group(self, group_id):
        return [
            order
            for order in self.get_all_virtual_startup_orders()
            if order.get(enums.StoredOrdersAttr.GROUP.value, {}).get(enums.StoredOrdersAttr.GROUP_ID.value, None)
            == group_id
        ]

    def get_all_virtual_startup_orders(self):
        return [
            order
            for order in self.startup_orders.values()
            if (
                # self-managed, ex: stop loss when not supported on exchange
                order.get(constants.STORAGE_ORIGIN_VALUE, {})
                .get(enums.ExchangeConstantsOrderColumns.SELF_MANAGED.value, False)
           ) or (
                # inactive, ex: OCO take profit when stop loss is supported on SPOT exchange
                order.get(constants.STORAGE_ORIGIN_VALUE, {})
                .get(enums.ExchangeConstantsOrderColumns.IS_ACTIVE.value, True) is False
            )
        ]

    @classmethod
    async def clear_database_history(cls, database, flush=True):
        await super().clear_database_history(database, flush=False)
        if cls.ENABLE_HISTORICAL_ORDER_UPDATES_STORAGE:
            await database.delete(cls.HISTORICAL_OPEN_ORDERS_TABLE, None)
        if flush:
            await database.flush()


def _get_group_dict(order):
    if not order.order_group:
        return {}
    try:
        return {
            enums.StoredOrdersAttr.GROUP_ID.value: order.order_group.name,
            enums.StoredOrdersAttr.GROUP_TYPE.value: order.order_group.__class__.__name__,
            enums.StoredOrdersAttr.ORDER_SWAP_STRATEGY.value: _get_active_order_swap_strategy_dict(
                order.order_group.active_order_swap_strategy
            ),
        }
    except KeyError:
        return {}


def _get_active_order_swap_strategy_dict(active_order_swap_strategy):
    try:
        return {
            enums.StoredOrdersAttr.STRATEGY_TIMEOUT.value: active_order_swap_strategy.swap_timeout,
            enums.StoredOrdersAttr.STRATEGY_TRIGGER_CONFIG.value:
                active_order_swap_strategy.trigger_price_configuration,
            enums.StoredOrdersAttr.STRATEGY_TYPE.value: active_order_swap_strategy.__class__.__name__,
        }
    except KeyError:
        return {}


def get_order_trailing_profile_dict(order):
    if not order.trailing_profile:
        return {}
    return {
        enums.StoredOrdersAttr.TRAILING_PROFILE_TYPE.value: order.trailing_profile.get_type().value,
        enums.StoredOrdersAttr.TRAILING_PROFILE_DETAILS.value: order.trailing_profile.to_dict(),
    }


def get_order_active_trigger_dict(order):
    if not order.active_trigger:
        return {}
    return {
        enums.StoredOrdersAttr.ACTIVE_TRIGGER_PRICE.value: float(order.active_trigger.trigger_price),
        enums.StoredOrdersAttr.ACTIVE_TRIGGER_ABOVE.value: order.active_trigger.trigger_above,
    }


def get_order_cancel_policy_dict(order):
    if not order.cancel_policy:
        return {}
    return {
        enums.StoredOrdersAttr.CANCEL_POLICY.value: order.cancel_policy.__class__.__name__,
        enums.StoredOrdersAttr.CANCEL_KWARGS.value: OrdersStorage.sanitize_for_storage(dataclasses.asdict(order.cancel_policy)),
    }


def _get_chained_orders(order, exchange_manager):
    if not order.chained_orders:
        return []
    return [
        _format_order(chained_order, exchange_manager)
        for chained_order in order.chained_orders
    ]


def _format_order(order, exchange_manager):
    try:
        formatted = {
            constants.STORAGE_ORIGIN_VALUE: OrdersStorage.sanitize_for_storage(order.to_dict()),
        }
        for key, val in (
            (enums.StoredOrdersAttr.EXCHANGE_CREATION_PARAMS, OrdersStorage.sanitize_for_storage(order.exchange_creation_params)),
            (enums.StoredOrdersAttr.TRADER_CREATION_KWARGS, OrdersStorage.sanitize_for_storage(order.trader_creation_kwargs)),
            (enums.StoredOrdersAttr.HAS_BEEN_BUNDLED, order.has_been_bundled),
            (enums.StoredOrdersAttr.ENTRIES, order.associated_entry_ids),
            (enums.StoredOrdersAttr.GROUP, _get_group_dict(order)),
            (enums.StoredOrdersAttr.TRAILING_PROFILE, get_order_trailing_profile_dict(order)),
            (enums.StoredOrdersAttr.ACTIVE_TRIGGER, get_order_active_trigger_dict(order)),
            (enums.StoredOrdersAttr.CANCEL_POLICY, get_order_cancel_policy_dict(order)),
            (enums.StoredOrdersAttr.CHAINED_ORDERS, _get_chained_orders(order, exchange_manager)),
            (enums.StoredOrdersAttr.UPDATE_WITH_TRIGGERING_ORDER_FEES, order.update_with_triggering_order_fees),
        ):
            # do not include default values
            if val:
                formatted[key.value] = val
        return formatted
    except Exception as err:
        commons_logging.get_logger(OrdersStorage.__name__).exception(err, True, f"Error when formatting order: {err}")
    return {}


def _format_order_update(exchange_manager, order_dict, update_type, update_time):
    order_id = order_dict[enums.ExchangeConstantsOrderColumns.ID.value]
    status = order_dict[enums.ExchangeConstantsOrderColumns.STATUS.value]
    order_update = {
        enums.StoredOrdersAttr.ORDER_ID.value: order_id,
        enums.StoredOrdersAttr.ORDER_STATUS.value: status,
        enums.StoredOrdersAttr.UPDATE_TIME.value: update_time,
        enums.StoredOrdersAttr.UPDATE_TYPE.value: update_type,
    }
    details = None
    try:
        details = _format_order(
            exchange_manager.exchange_personal_data.orders_manager.get_order(order_id),
            exchange_manager
        )
    except KeyError:
        if status == enums.OrderStatus.OPEN.value:
            # ensure order details are present in open orders
            details = {
                constants.STORAGE_ORIGIN_VALUE: OrdersStorage.sanitize_for_storage(order_dict),
            }
    order_update[enums.StoredOrdersAttr.ORDER_DETAILS.value] = details
    return order_update


def from_order_document(order_document):
    order_dict = dict(order_document)
    try:
        restore_order_storage_origin_value(order_dict[constants.STORAGE_ORIGIN_VALUE])
        for chained_order in order_dict.get(enums.StoredOrdersAttr.CHAINED_ORDERS.value, []):
            from_order_document(chained_order)
    except Exception as err:
        commons_logging.get_logger(OrdersStorage.__name__).exception(
            err, True, f"Error when reading: {err} order: {order_document}"
        )
    return order_dict


def restore_order_storage_origin_value(origin_val):
    origin_val[enums.ExchangeConstantsOrderColumns.AMOUNT.value] = \
        decimal.Decimal(str(origin_val[enums.ExchangeConstantsOrderColumns.AMOUNT.value]))
    origin_val[enums.ExchangeConstantsOrderColumns.COST.value] = \
        decimal.Decimal(str(origin_val[enums.ExchangeConstantsOrderColumns.COST.value]))
    origin_val[enums.ExchangeConstantsOrderColumns.FILLED.value] = \
        decimal.Decimal(str(origin_val[enums.ExchangeConstantsOrderColumns.FILLED.value]))
    origin_val[enums.ExchangeConstantsOrderColumns.PRICE.value] = \
        decimal.Decimal(str(origin_val[enums.ExchangeConstantsOrderColumns.PRICE.value]))
    if origin_val[enums.ExchangeConstantsOrderColumns.FEE.value] and \
            enums.FeePropertyColumns.COST.value in origin_val[enums.ExchangeConstantsOrderColumns.FEE.value]:
        origin_val[enums.ExchangeConstantsOrderColumns.FEE.value][enums.FeePropertyColumns.COST.value] = \
            decimal.Decimal(str(
                origin_val[enums.ExchangeConstantsOrderColumns.FEE.value][enums.FeePropertyColumns.COST.value]
            ))
    return origin_val


def _get_startup_order_key(order_dict):
    # use exchange id if available, fallback to order_id (for self managed orders)
    return order_dict[constants.STORAGE_ORIGIN_VALUE][enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value] or \
        order_dict[constants.STORAGE_ORIGIN_VALUE][enums.ExchangeConstantsOrderColumns.ID.value]
