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
import asyncio

import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.exchanges as exchanges
import octobot_trading.constants as constants
import octobot_trading.errors as errors
import octobot_trading.enums as enums
import octobot_trading.personal_data.orders.orders_storage_operations as orders_storage_operations


class OrdersProducer(exchanges_channel.ExchangeChannelProducer):
    async def push(self, orders, is_from_bot=False, are_closed=False):
        await self.perform(orders, is_from_bot=is_from_bot, are_closed=are_closed)

    async def perform(self, orders, is_from_bot=False, are_closed=False):
        try:
            self.logger.debug(f"Received order update for {len(orders)}{' closed' if are_closed else ''} orders.")
            has_new_order = False
            waiting_complete_init_orders = []
            symbols = set()
            pending_groups = {}  # Used when restoring orders from order storage:
            # a dict of order groups for which to check if associated self-managed orders are to be created
            for order in orders:
                exchange_order_id: str = self.channel.exchange_manager.exchange.parse_exhange_order_id(order)
                symbol = self.channel.exchange_manager.get_exchange_symbol(
                    self.channel.exchange_manager.exchange.parse_order_symbol(order)
                )
                if self.channel.exchange_manager.exchange.is_creating_order(order, symbol):
                    # ignore orders that are being created
                    self.logger.debug(
                        f"Ignored update from order channel for {symbol} order with exchange order id "
                        f"{exchange_order_id} as "
                        f"this order is being created and will automatically be updated once creation is complete."
                    )
                    continue
                symbols.add(symbol)

                # if this order was not managed by order_manager before
                is_new_order = not self.channel.exchange_manager.exchange_personal_data.orders_manager. \
                    has_order(None, exchange_order_id=exchange_order_id)
                has_new_order |= is_new_order

                # update this order
                if are_closed:
                    await self._handle_close_order_update(exchange_order_id, order)
                else:
                    try:
                        # will add a group to pending_groups if a group is restored from orders storage
                        await self._handle_open_order_update(
                            symbol, order, exchange_order_id, is_from_bot, is_new_order, pending_groups
                        )
                    except errors.PortfolioNegativeValueError:
                        # Special case for new orders: their order init does not finish properly when this happens
                        if is_new_order and self.channel.exchange_manager.exchange_personal_data.orders_manager. \
                           has_order(None, exchange_order_id=exchange_order_id):
                            new_order = self.channel.exchange_manager.exchange_personal_data.orders_manager.get_order(
                                None, exchange_order_id=exchange_order_id
                            )
                            # Order init might have failed due to a portfolio update on the exchange side
                            # (added funds, etc).
                            waiting_complete_init_orders.append(new_order)
                        else:
                            # order was not even added to orders_manager: another issue happened, raise
                            raise
            if not are_closed:
                if pending_groups:
                    await orders_storage_operations.create_missing_virtual_orders_from_storage_order_groups(
                        pending_groups, self.channel.exchange_manager
                    )
                await self.handle_post_open_orders_update(
                    symbols, orders, waiting_complete_init_orders, has_new_order, is_from_bot
                )

        except asyncio.CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.exception(e, True, f"Exception when triggering update: {e}")

    async def _restore_required_virtual_orders(self):
        """
        Restore virtual orders that would not be restored otherwise
        Should only be called once or will create the same virtual orders multiple times
        """
        pending_groups = {}
        await orders_storage_operations.create_required_virtual_orders(
            pending_groups, self.channel.exchange_manager
        )

    async def _handle_open_order_update(
        self, symbol, order_dict, exchange_order_id, is_from_bot, is_new_order, pending_groups
    ):
        """
        Create or update an open Order from exchange data
        :param symbol: the order symbol
        :param order_dict: the order dict
        :param exchange_order_id: the order id on exchange
        :param is_from_bot: If the order was created by OctoBot
        :param is_new_order: True if this open order has been created
        :param pending_groups: dict of groups to be created
        """
        changed, order = await self.channel.exchange_manager.exchange_personal_data.handle_order_update_from_raw(
            exchange_order_id, order_dict, is_new_order=is_new_order, should_notify=False
        )
        if changed:
            if is_new_order and \
                    not self.channel.exchange_manager.exchange_personal_data.orders_manager.\
                    are_exchange_orders_initialized:
                try:
                    # when fetching initial orders, complete them with storage data when possible
                    await self.channel.exchange_manager.exchange_personal_data.update_order_from_stored_data(
                        order.exchange_order_id,
                        pending_groups,
                    )
                except Exception as err:
                    self.logger.exception(err, True, f"Error when completing order with stored data: {err}")
            await self.send(
                self.channel.exchange_manager.exchange.get_pair_cryptocurrency(symbol),
                symbol,
                order.to_dict(),
                is_from_bot=is_from_bot,
                update_type=enums.OrderUpdateType.NEW if is_new_order else enums.OrderUpdateType.STATE_CHANGE,
                is_closed=False
            )

    async def _complete_open_order_init(self, orders, is_from_bot):
        """
        Called when open order init failed due to a portfolio sync issue, will now complete their init
        """
        for order in orders:
            self.logger.debug(f"Completing order init for order: {order}")
            await self.channel.exchange_manager.exchange_personal_data.on_order_refresh_success(order, False, False)
            await self.send(
                self.channel.exchange_manager.exchange.get_pair_cryptocurrency(order.symbol),
                order.symbol,
                order.to_dict(),
                is_from_bot=is_from_bot,
                update_type=enums.OrderUpdateType.NEW,
                is_closed=False
            )

    async def _handle_close_order_update(self, exchange_order_id, raw_order):
        """
        Create or update a close Order from exchange data
        :param exchange_order_id: the order id
        :param raw_order: the order dict
        """
        await self.channel.exchange_manager.exchange_personal_data.handle_closed_order_update(
            exchange_order_id, raw_order
        )

    async def handle_post_open_orders_update(
        self, symbols, orders, waiting_complete_init_orders, has_new_order, is_from_bot
    ):
        """
        Perform post open Order update actions :
        - 1. Check if some previously known open order has not been found during update
        - 2. Force portfolio refresh if a new order has been loaded or waiting a init order exists
        - 3. Complete order init process when necessary
        :param symbols: the updated orders symbols
        :param orders: the updated orders dicts
        :param waiting_complete_init_orders: orders which init process should be completed after portfolio refresh
        :param has_new_order: if a new order has been loaded
        :param is_from_bot: If the order was created by OctoBot
        :return:
        """
        for symbol in symbols:
            await self._check_missing_open_orders(symbol, orders)

        # if a new order have been loaded : refresh portfolio to ensure available funds are up to date
        if has_new_order or waiting_complete_init_orders:
            await exchanges_channel.get_chan(constants.BALANCE_CHANNEL,
                                             self.channel.exchange_manager.id).get_internal_producer(). \
                refresh_real_trader_portfolio()
        if waiting_complete_init_orders:
            self.logger.debug(
                f"Completing order init after portfolio sync for {len(waiting_complete_init_orders)} orders"
            )
            await self._complete_open_order_init(waiting_complete_init_orders, is_from_bot)

    async def update_order_from_exchange(self, order,
                                         should_notify=False,
                                         wait_for_refresh=False,
                                         force_job_execution=False,
                                         create_order_producer_if_missing=True):
        """
        Update order from exchange
        :param order: the order to update
        :param wait_for_refresh: if True, wait until the order refresh task to finish
        :param should_notify: if Orders channel consumers should be notified
        :param force_job_execution: When True, order_update_job will bypass its dependencies check
        :param create_order_producer_if_missing: Should be set to False when called by self to prevent spamming
        :return: True if the order was updated
        """
        try:
            await (exchanges_channel.get_chan(constants.ORDERS_CHANNEL, self.channel.exchange_manager.id).producers[-1].
                   update_order_from_exchange(order=order,
                                              should_notify=should_notify,
                                              force_job_execution=force_job_execution,
                                              wait_for_refresh=wait_for_refresh))
        except IndexError:
            if not self.channel.exchange_manager.is_simulated and create_order_producer_if_missing:
                self.logger.info("Missing orders producer, starting one...")
                await exchanges.create_authenticated_producer_from_parent(self.channel.exchange_manager,
                                                                          self.__class__,
                                                                          force_register_producer=True)
                await self.update_order_from_exchange(order=order,
                                                      should_notify=should_notify,
                                                      wait_for_refresh=wait_for_refresh,
                                                      force_job_execution=force_job_execution,
                                                      create_order_producer_if_missing=False)

    async def _check_missing_open_orders(self, symbol, orders):
        """
        Check if there is no missing open orders in order_manager compared to exchange open orders
        :param symbol: the order symbol
        :param orders: open orders from exchange
        """
        missing_exchange_order_ids = list(
            set(
                order.exchange_order_id for order in
                self.channel.exchange_manager.exchange_personal_data.orders_manager.get_open_orders(
                    symbol, active=True
                ) + self.channel.exchange_manager.exchange_personal_data.orders_manager.get_pending_cancel_orders(
                    symbol, active=True
                )
                if not (order.is_cleared() or order.is_self_managed())) -
            set(
                self.channel.exchange_manager.exchange.parse_exhange_order_id(order)
                for order in orders
            )
        )
        if missing_exchange_order_ids:
            self.logger.info(
                f"{len(missing_exchange_order_ids)} open orders are missing on exchange, "
                f"synchronizing with exchange (exchange ids: {missing_exchange_order_ids})..."
            )
            synchronize_tasks = []
            for missing_order_id in missing_exchange_order_ids:
                try:
                    order_to_update = self.channel.exchange_manager.exchange_personal_data.orders_manager. \
                        get_order(None, exchange_order_id=missing_order_id)
                    if order_to_update.state is not None:
                        # catch exception not to prevent multiple synchronize to be cancelled in asyncio.gather
                        synchronize_tasks.append(
                            order_to_update.state.synchronize(force_synchronization=True, catch_exception=True)
                        )
                except KeyError:
                    self.logger.error(
                        f"Order with id {missing_order_id} could not be synchronized: missing from order manager"
                    )
            await asyncio.gather(*synchronize_tasks)

    async def send(
        self, cryptocurrency, symbol, order, is_from_bot=True,
        update_type=enums.OrderUpdateType.STATE_CHANGE, is_closed=False
    ):
        if is_closed or update_type is enums.OrderUpdateType.CLOSED:
            # do not push closed orders
            return
        for consumer in self.channel.get_filtered_consumers(symbol=symbol):
            await consumer.queue.put({
                "exchange": self.channel.exchange_manager.exchange_name,
                "exchange_id": self.channel.exchange_manager.id,
                "cryptocurrency": cryptocurrency,
                "symbol": symbol,
                "order": order,
                "update_type": update_type.value,
                "is_from_bot": is_from_bot
            })


class OrdersChannel(exchanges_channel.ExchangeChannel):
    PRODUCER_CLASS = OrdersProducer
    CONSUMER_CLASS = exchanges_channel.ExchangeChannelConsumer
