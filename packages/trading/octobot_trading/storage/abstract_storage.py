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
import asyncio
import contextlib
import copy
import decimal
import time
import types

import octobot_commons.display as commons_display
import octobot_commons.logging as logging

import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.constants as trading_constants
import octobot_trading.exchanges as exchanges


class AbstractStorage:
    IS_LIVE_CONSUMER = True
    USE_LIVE_CONSUMER_IN_BACKTESTING = False
    LIVE_CHANNEL = None
    IS_HISTORICAL = True
    HISTORY_TABLE = None
    FLUSH_DEBOUNCE_DURATION = 5   # avoid disc spam on multiple quick live updated
    IS_MULTI_EXCHANGE_STORAGE = False   # set True when this storage is updating data from all other exchanges as well
    LAST_UPDATE_TIME_PER_MATRIX_ID = {}

    def __init__(self, exchange_manager, plot_settings: commons_display.PlotSettings,
                 use_live_consumer_in_backtesting=None, is_historical=None):
        self.exchange_manager = exchange_manager
        self.plot_settings: commons_display.PlotSettings = plot_settings
        self.consumer = None
        self.use_live_consumer_in_backtesting = use_live_consumer_in_backtesting \
            or self.USE_LIVE_CONSUMER_IN_BACKTESTING
        self.is_historical = is_historical or self.IS_HISTORICAL
        self.enabled = True
        self._update_task = None
        self._flush_task = None
        self._to_update_auth_data_ids_buffer = set()

    def should_register_live_consumer(self):
        return self.IS_LIVE_CONSUMER and \
           (
                not self.exchange_manager.is_backtesting or
                (self.exchange_manager.is_backtesting and self.use_live_consumer_in_backtesting)
            )

    async def start(self):
        if self.should_register_live_consumer():
            await self.register_live_consumer()
        await self.on_start()

    async def on_start(self):
        """
        Called after start, implement in necessary
        """

    async def register_live_consumer(self):
        if self.LIVE_CHANNEL is None:
            raise ValueError(f"self.live_channel has to be set")
        self.consumer = await exchanges_channel.get_chan(
            self.LIVE_CHANNEL,
            self.exchange_manager.id
        ).new_consumer(
            self._live_callback
        )

    async def enable(self, enabled):
        if self.enabled != enabled:
            self.enabled = enabled
            if self.enabled:
                await self.start()
            else:
                await self.stop(clear=False)

    async def stop(self, clear=True):
        if self.consumer is not None:
            await self.consumer.stop()
        for task in (self._update_task, self._flush_task):
            if task is not None and not task.done():
                task.cancel()
        if clear:
            self.consumer = None
            self.exchange_manager = None

    async def store_history(self):
        if self.enabled:
            await self._store_history()

    async def trigger_debounced_update_auth_data(self, reset: bool):
        if self.exchange_manager.is_backtesting:
            # no interest in backtesting data
            return
        if self._update_task is not None and not self._update_task.done():
            self._update_task.cancel()
        self._update_task = asyncio.create_task(self._waiting_update_auth_data(reset))

    async def trigger_debounced_flush(self):
        if self.exchange_manager.is_backtesting:
            # flush now in backtesting
            await self.flush()
            return
        if self._flush_task is not None and not self._flush_task.done():
            self._flush_task.cancel()
        self._flush_task = asyncio.create_task(self._waiting_flush())

    async def get_history(self):
        # override if necessary
        return [
            copy.copy(document[trading_constants.STORAGE_ORIGIN_VALUE])
            for document in await self._get_db().all(self.HISTORY_TABLE)
            if trading_constants.STORAGE_ORIGIN_VALUE in document
        ]

    async def _waiting_update_auth_data(self, reset):
        try:
            debounce_interval = trading_constants.AUTH_UPDATE_DEBOUNCE_DURATION
            await asyncio.sleep(debounce_interval)
            with self._multi_exchange_auth_value_update(debounce_interval) as should_update:
                if should_update:
                    await self._update_auth_data(reset)
                else:
                    logging.get_logger(self.__class__.__name__).debug(
                        f"Skip storage update: this multi exchange value has already been updated."
                    )
        except Exception as err:
            logging.get_logger(self.__class__.__name__).exception(err, True, f"Error when updating auth data: {err}")

    async def _waiting_flush(self):
        try:
            await asyncio.sleep(self.FLUSH_DEBOUNCE_DURATION)
            await self.flush()

        except Exception as err:
            logging.get_logger(self.__class__.__name__).exception(err, True, f"Error when flushing database: {err}")

    async def _update_auth_data(self, reset):
        pass

    async def _live_callback(self, *args, **kwargs):
        raise NotImplementedError(f"_live_callback not implemented for {self.__class__.__name__}")

    async def _store_history(self):
        raise NotImplementedError(f"_store_history not implemented for {self.__class__.__name__}")

    def _get_db(self, *args):
        raise NotImplementedError(f"_get_db not implemented for {self.__class__.__name__}")

    async def clear_history(self, flush=True):
        await self.clear_database_history(self._get_db(), flush=flush)

    async def flush(self):
        await self._get_db().flush()

    @contextlib.contextmanager
    def _multi_exchange_auth_value_update(self, interval):
        """
        yields True if the auth updated value should be updated at the current time or if it already just got updated
        """
        if not self.IS_MULTI_EXCHANGE_STORAGE:
            yield True
            return
        should_update = time.time() - self._get_multi_exchange_last_update_time() > interval
        if should_update:
            # update time twice to prevent concurrent updated during yield
            self._register_multi_exchange_last_update_time()
            yield True
            self._register_multi_exchange_last_update_time()
        else:
            yield False

    def _get_multi_exchange_last_update_time(self) -> float:
        try:
            return AbstractStorage.LAST_UPDATE_TIME_PER_MATRIX_ID[
                exchanges.Exchanges.instance().get_matrix_id(self.exchange_manager)
            ][self.__class__.__name__]
        except KeyError:
            return 0

    def _register_multi_exchange_last_update_time(self):
        try:
            AbstractStorage.LAST_UPDATE_TIME_PER_MATRIX_ID[
                exchanges.Exchanges.instance().get_matrix_id(self.exchange_manager)
            ][self.__class__.__name__] = time.time()
        except KeyError:
            AbstractStorage.LAST_UPDATE_TIME_PER_MATRIX_ID[
                exchanges.Exchanges.instance().get_matrix_id(self.exchange_manager)
            ] = {
                self.__class__.__name__: time.time()
            }

    @classmethod
    async def clear_database_history(cls, database, flush=True):
        if cls.HISTORY_TABLE is None:
            raise NotImplementedError(f"{cls.__name__}.HISTORY_TABLE has to be set")
        await database.delete(cls.HISTORY_TABLE, None)
        if flush:
            await database.flush()

    @classmethod
    def sanitize_for_storage(cls, element: dict) -> dict:
        sanitized = copy.copy(element)
        for key, val in element.items():
            if isinstance(val, decimal.Decimal):
                sanitized[key] = float(val)
            elif isinstance(val, dict):
                sanitized[key] = cls.sanitize_for_storage(val)
            elif isinstance(val, types.FunctionType):
                raise ValueError(f"{val.__name__} is a function, it can't be serialized")
        return sanitized

    @staticmethod
    def hard_reset_and_retry_if_necessary(fn):
        """
        Will retry the given function if a database hard reset error is raised
        Warning: when it happens, will also completely reset the database
        """
        async def wrapper(*args, **kwargs):
            try:
                return await fn(*args, **kwargs)
            except Exception as err:
                database = args[0]._get_db()    # pylint: disable=protected-access
                if database.is_hard_reset_error(err):
                    logging.get_logger(args[0].__class__.__name__).warning(
                        f"Resetting database due to [{err}] error"
                    )
                    await database.hard_reset()
                    return await fn(*args, **kwargs)
                raise
        return wrapper
