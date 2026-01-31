# pylint: disable=E0611
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

import octobot_commons.async_job as async_job
import octobot_commons.tree as commons_tree
import octobot_commons.enums as commons_enums
import octobot_commons.html_util as html_util

import octobot_trading.errors as errors
import octobot_trading.personal_data.orders.channel.orders as orders_channel
import octobot_trading.constants as constants


class OrdersUpdater(orders_channel.OrdersProducer):
    # set True if this channels should be notified when traded symbols are updated
    TO_NOTIFY_ON_TRADED_SYMBOLS_UPDATE: bool = True
    """
    Update open and close orders from exchange
    Can also be used to update a specific order from exchange
    """

    CHANNEL_NAME = constants.ORDERS_CHANNEL
    ORDERS_UPDATE_LIMIT = None
    ORDERS_STARTING_REFRESH_TIME = 10
    OPEN_ORDER_REFRESH_TIME = 7
    CLOSE_ORDER_REFRESH_TIME = 81
    TIME_BETWEEN_ORDERS_REFRESH = 2
    DEPENDENCIES_TIMEOUT = 30
    OPEN_ORDER_INITIAL_FETCH_GIVE_UP_TIMEOUT = 30

    def __init__(self, channel):
        super().__init__(channel)

        self._is_initialized_event_set = False
        # create async jobs
        self.open_orders_job = async_job.AsyncJob(self._open_orders_fetch_and_push,
                                                  execution_interval_delay=self.OPEN_ORDER_REFRESH_TIME,
                                                  min_execution_delay=self.TIME_BETWEEN_ORDERS_REFRESH)
        self.closed_orders_job = async_job.AsyncJob(self._closed_orders_fetch_and_push,
                                                    execution_interval_delay=self.CLOSE_ORDER_REFRESH_TIME,
                                                    min_execution_delay=self.TIME_BETWEEN_ORDERS_REFRESH)
        self.order_update_job = async_job.AsyncJob(self._order_fetch_and_push,
                                                   is_periodic=False,
                                                   enable_multiple_runs=True)
        self.order_update_job.add_job_dependency(self.open_orders_job)
        self.open_orders_job.add_job_dependency(self.order_update_job)

    async def initialize(self) -> None:
        """
        Initialize data before starting jobs
        """
        try:
            await self.wait_for_dependencies(
                [
                    commons_tree.get_exchange_path(
                        self.channel.exchange_manager.exchange_name,
                        commons_enums.InitializationEventExchangeTopics.CONTRACTS.value
                    ),
                    commons_tree.get_exchange_path(
                        self.channel.exchange_manager.exchange_name,
                        commons_enums.InitializationEventExchangeTopics.POSITIONS.value
                    ),
                ],
                self.DEPENDENCIES_TIMEOUT
            )
            await self.fetch_and_push(is_from_bot=False, retry_till_success=True)
            await self._restore_required_virtual_orders()
        except errors.NotSupported:
            self.logger.error(f"{self.channel.exchange_manager.exchange_name} is not supporting open orders updates")
            await self.pause()
        except Exception as e:
            self.logger.exception(e, True, f"Fail to initialize orders : {html_util.get_html_summary_if_relevant(e)}")

    async def start(self) -> None:
        """
        Start updater jobs
        """
        await self.initialize()
        await asyncio.sleep(self.ORDERS_STARTING_REFRESH_TIME)
        await self.open_orders_job.run(retry_attempts=1)
        # await self.closed_orders_job.run()

    async def fetch_and_push(self, is_from_bot=True, limit=ORDERS_UPDATE_LIMIT, retry_till_success=False):
        """
        Update open and closed orders from exchange
        :param is_from_bot: True if the order was created by OctoBot
        :param limit: the exchange request orders count limit
        :param retry_till_success: retry request till it works. Should be rarely used as it might take some time
        """
        # should not raise: open orders are necessary
        try:
            await self._open_orders_fetch_and_push(is_from_bot=is_from_bot, limit=limit,
                                                   retry_till_success=retry_till_success)
        finally:
            if self.channel is not None:
                self.channel.exchange_manager.exchange_personal_data.on_completed_orders_fetch()
        await asyncio.sleep(self.TIME_BETWEEN_ORDERS_REFRESH)
        try:
            # can raise, closed orders are not critical data
            await self._closed_orders_fetch_and_push(limit=limit)
        except errors.NotSupported:
            self.logger.debug(f"{self.channel.exchange_manager.exchange_name} is not supporting closed orders updates")

    async def _open_orders_fetch_and_push(
        self, is_from_bot=True, limit=ORDERS_UPDATE_LIMIT, retry_till_success=False, retry_attempts=0
    ):
        """
        Update open orders from exchange
        :param is_from_bot: True if the order was created by OctoBot
        :param limit: the exchange request orders count limit
        :param retry_till_success: retry request till it works. Should be rarely used as it might take some time
        :param retry_attempts: how many times to retry before failing
        """
        for symbol in self._get_pairs_to_update():
            await self._symbol_orders_fetch_and_push(symbol)
            if not self._is_initialized_event_set:
                self._set_initialized_event(symbol)
        self._is_initialized_event_set = True

    async def _symbol_orders_fetch_and_push(self, symbol: str, is_from_bot=True, limit=ORDERS_UPDATE_LIMIT, retry_till_success=False, retry_attempts=0):
        """
        Update open orders from exchange for a specific symbol
        :param symbol: the symbol to update
        :param is_from_bot: True if the order was created by OctoBot
        :param limit: the exchange request orders count limit
        :param retry_till_success: retry request till it works. Should be rarely used as it might take some time
        :param retry_attempts: how many times to retry before failing
        """
        if retry_till_success:
            open_orders: list = await self.channel.exchange_manager.exchange.retry_till_success(
                self.OPEN_ORDER_INITIAL_FETCH_GIVE_UP_TIMEOUT,
                self.channel.exchange_manager.exchange.get_open_orders, symbol=symbol, limit=limit,
            )
        elif retry_attempts:
            open_orders: list = await self.channel.exchange_manager.exchange.retry_n_time(
                retry_attempts,
                self.channel.exchange_manager.exchange.get_open_orders, symbol=symbol, limit=limit,
            )
        else:
            open_orders: list = await self.channel.exchange_manager.exchange.get_open_orders(
                symbol=symbol, limit=limit
            )
        if open_orders:
            await self.push(open_orders, is_from_bot=is_from_bot)
        else:
            await self.handle_post_open_orders_update((symbol, ), open_orders, [], False, True)

    def _set_initialized_event(self, symbol):
        # set init in updater as it's the only place we know if we fetched orders or not regardless of orders existence
        commons_tree.EventProvider.instance().trigger_event(
            self.channel.exchange_manager.bot_id, commons_tree.get_exchange_path(
                self.channel.exchange_manager.exchange_name,
                commons_enums.InitializationEventExchangeTopics.ORDERS.value,
                symbol=symbol
            )
        )

    async def _closed_orders_fetch_and_push(self, limit=ORDERS_UPDATE_LIMIT) -> None:
        """
        Update closed orders from exchange
        :param limit: the exchange request orders count limit
        """
        for symbol in self._get_pairs_to_update():
            close_orders: list = await self.channel.exchange_manager.exchange.get_closed_orders(
                symbol=symbol, limit=limit)

            if close_orders:
                await self.push(close_orders, are_closed=True)

    async def update_order_from_exchange(self, order,
                                         should_notify=False,
                                         wait_for_refresh=False,
                                         force_job_execution=False,
                                         create_order_producer_if_missing=True):
        """
        Trigger order job refresh from exchange
        :param order: the order to update
        :param wait_for_refresh: if True, wait until the order refresh task to finish
        :param should_notify: if Orders channel consumers should be notified
        :param force_job_execution: When True, order_update_job will bypass its dependencies check
        :param create_order_producer_if_missing: Should be set to False when called by self to prevent spamming
        :return: True if the order was updated
        """
        await self.order_update_job.run(force=True, wait_for_task_execution=wait_for_refresh,
                                        ignore_dependencies_check=force_job_execution,
                                        order=order, should_notify=should_notify)

    async def _order_fetch_and_push(self, order, should_notify=False):
        """
        Update Order from exchange
        :param order: the order to update
        :param should_notify: if Orders channel consumers should be notified
        :return: True if the order was updated
        """
        exchange_name = self.channel.exchange_manager.exchange_name
        self.logger.info(f"Requested update for {order} on {exchange_name}")
        raw_order = await self.channel.exchange_manager.exchange.get_order(
            order.exchange_order_id, order.symbol, order_type=order.order_type
        )

        if raw_order is not None:
            self.logger.info(f"Received update for {order} on {exchange_name}: {raw_order}")
            await self.channel.exchange_manager.exchange_personal_data.handle_order_update_from_raw(
                order.exchange_order_id, raw_order, should_notify=should_notify
            )
            self.logger.info(f"Completed update for {order} on {exchange_name}")
        else:
            self.logger.info(f"Can't received update for {order} on {exchange_name}: received order is None")

    def _should_run(self):
        return self.channel.exchange_manager.exchange.is_successfully_authenticated()

    async def modify(self, added_pairs=None, removed_pairs=None):
        if not self._should_run():
            return
        if added_pairs:
            for symbol in added_pairs:
                self.logger.info(f"Fetching orders for new traded symbol: {symbol}...")
                await self._symbol_orders_fetch_and_push(symbol)

    def _get_pairs_to_update(self):
        return self.channel.exchange_manager.exchange_config.traded_symbol_pairs + self.channel.exchange_manager.exchange_config.additional_traded_pairs

    async def stop(self) -> None:
        """
        Stop producer by stopping its jobs
        """
        await super().stop()
        self.open_orders_job.stop()
        self.closed_orders_job.stop()
        self.order_update_job.stop()

    async def resume(self) -> None:
        """
        Resume producer by restarting its jobs
        """
        await super().resume()
        if not self.is_running:
            await self.run()
