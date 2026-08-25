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
import typing

import octobot_commons.tree as commons_tree
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.html_util as html_util
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.logging as logging

import octobot_trading.errors as errors
import octobot_trading.personal_data.trades.trade_factory as trade_factory_module
import octobot_trading.personal_data.trades.channel as trades_channel
import octobot_trading.constants as constants
import octobot_trading.util as util


class TradesUpdater(trades_channel.TradesProducer):
    """
    The Trades Update fetch the exchange trades and send it to the Trade Channel
    """

    """
    The updater related channel name
    """
    CHANNEL_NAME = constants.TRADES_CHANNEL

    """
    Trades history request limit
    """
    MAX_OLD_TRADES_TO_FETCH = 100
    TRADES_LIMIT = 10

    """
    The default trade history update refresh time in seconds
    """
    TRADES_REFRESH_TIME = 5 * commons_constants.MINUTE_TO_SECONDS

    DEPENDENCIES_TIMEOUT = 5 * commons_constants.MINUTE_TO_SECONDS

    def __init__(self, channel):
        super().__init__(channel)

        self._is_initialized_event_set = False

    async def init_trade_history(self):
        try:
            await self.fetch_and_push()
            self._set_all_initialized()
            await asyncio.sleep(self.TRADES_REFRESH_TIME)
        except errors.NotSupported:
            self.logger.warning(f"{self.channel.exchange_manager.exchange_name} is not supporting updates")
            await self.pause()
        except Exception as error:
            self.logger.error(f"Fail to initialize trade history : {html_util.get_html_summary_if_relevant(error)}")

    @staticmethod
    async def _fetch_trades_for_symbol(
        exchange,
        symbol: str,
        *,
        limit: int | None = None,
        exhaust_history: bool = False,
    ) -> list:
        if exhaust_history:
            return await exchange.get_my_recent_trades(symbol=symbol, exhaust_history=True)
        return await exchange.get_my_recent_trades(symbol=symbol, limit=limit)

    async def fetch_trades(
        self,
        symbols: list[str],
        limit: int = MAX_OLD_TRADES_TO_FETCH,
        *,
        exhaust_history: bool = False,
    ) -> list:
        """
        Fetch recent trades from the exchange for the given symbols.
        This is the only method that calls exchange.get_my_recent_trades.
        When exhaust_history is True and symbols is empty, fetches account-wide history.
        """
        exchange = self.channel.exchange_manager.exchange
        if exhaust_history and not symbols:
            trades = await exchange.get_my_recent_trades(symbol=None, exhaust_history=True)
            return trades or []
        if not symbols:
            return []

        if len(symbols) == 1:
            trades = await TradesUpdater._fetch_trades_for_symbol(
                exchange, symbols[0], limit=limit, exhaust_history=exhaust_history,
            )
            return trades or []

        trade_batches = await asyncio_tools.gather_waiting_for_all_before_raising(
            *[
                TradesUpdater._fetch_trades_for_symbol(
                    exchange, trading_symbol, limit=limit, exhaust_history=exhaust_history,
                )
                for trading_symbol in symbols
            ]
        )
        aggregated_trades: list = []
        for trade_batch in trade_batches:
            aggregated_trades.extend(trade_batch or [])
        return aggregated_trades

    async def fetch_and_push(self):
        self.logger.debug(
            f"Updating {self.channel.exchange_manager.exchange_config.traded_symbol_pairs} trades history"
        )
        for symbol in self._get_pairs_to_update():            
            if trades := await self.fetch_trades([symbol], limit=self.MAX_OLD_TRADES_TO_FETCH):
                await self.push(trades)

    @staticmethod
    def ensure_parsing(exchange_manager, raw_trade: dict) -> typing.Optional[dict]:
        try:
            return trade_factory_module.create_trade_instance_from_raw(
                exchange_manager.trader, raw_trade
            ).to_dict()
        except Exception as error:
            logging.get_logger("TradesUpdater").exception(
                error,
                True,
                f"Unexpected error when parsing [{exchange_manager.exchange_name}] trade "
                f"({error} {error.__class__.__name__}), trade: {raw_trade}. Ignored trade.",
            )
        return None

    def _set_all_initialized(self):
        for symbol in self._get_pairs_to_update():
            if not self._is_initialized_event_set:
                self._set_initialized_event(symbol)
        self._is_initialized_event_set = True

    def _set_initialized_event(self, symbol):
        # set init in updater as it's the only place we know if we fetched trades or not regardless of trades existence
        commons_tree.EventProvider.instance().trigger_event(
            self.channel.exchange_manager.bot_id, commons_tree.get_exchange_path(
                self.channel.exchange_manager.exchange_name,
                commons_enums.InitializationEventExchangeTopics.TRADES.value,
                symbol=symbol
            )
        )

    async def start(self):
        if util.is_trade_history_loading_enabled(self.channel.exchange_manager.config):
            await self.wait_for_dependencies(
                [
                    commons_tree.get_exchange_path(
                        self.channel.exchange_manager.exchange_name,
                        commons_enums.InitializationEventExchangeTopics.CONTRACTS.value
                    ),
                ],
                self.DEPENDENCIES_TIMEOUT
            )
            await self.init_trade_history()

    async def _run_update_loop(self):
        while not self.should_stop and not self.channel.is_paused:
            try:
                await self.fetch_and_push()
            except Exception as error:
                self.logger.error(f"Fail to update trades : {html_util.get_html_summary_if_relevant(error)}")

            await asyncio.sleep(self.TRADES_REFRESH_TIME)

    def _get_pairs_to_update(self):
        return self.channel.exchange_manager.exchange_config.traded_symbol_pairs + self.channel.exchange_manager.exchange_config.additional_traded_pairs

    async def resume(self) -> None:
        """
        Resume updater process
        """
        await super().resume()
        if not self.is_running:
            await self.run()
