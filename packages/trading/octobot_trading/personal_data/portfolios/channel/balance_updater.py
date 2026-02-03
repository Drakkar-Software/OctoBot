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
import decimal

import octobot_commons.logging as logging
import octobot_commons.html_util as html_util

import octobot_commons.async_job as async_job
import octobot_trading.errors as errors
import octobot_trading.constants as constants
import octobot_trading.personal_data.portfolios.channel.balance as portfolios_channel
import octobot_trading.exchange_channel as exchange_channel


class BalanceUpdater(portfolios_channel.BalanceProducer):
    """
    The Balance Update fetch the exchange portfolio and send it to the Balance Channel
    """

    """
    The default balance update refresh time in seconds
    """
    REGULAR_PORTFOLIO_UPDATE_TIME = 666
    EXPECTED_PORTFOLIO_UPDATE_TIME = 20
    TIME_BETWEEN_PORTFOLIO_UPDATES = 10

    """
    The updater related channel name
    """
    CHANNEL_NAME = constants.BALANCE_CHANNEL

    def __init__(self, channel):
        super().__init__(channel)
        # regular_portfolio_update_job should always run
        self.regular_portfolio_update_job = async_job.AsyncJob(
            self._fetch_and_push_portfolio,
            execution_interval_delay=self.REGULAR_PORTFOLIO_UPDATE_TIME,
            min_execution_delay=self.TIME_BETWEEN_PORTFOLIO_UPDATES
        )
        # temporary_expected_portfolio_update_job should run only when expected portfolio update is needed
        self.temporary_expected_portfolio_update_job = async_job.AsyncJob(
            self._fetch_and_push_portfolio,
            execution_interval_delay=self.EXPECTED_PORTFOLIO_UPDATE_TIME,
            min_execution_delay=self.TIME_BETWEEN_PORTFOLIO_UPDATES
        )
        self.temporary_expected_portfolio_update_job.add_job_dependency(self.regular_portfolio_update_job)
        self.regular_portfolio_update_job.add_job_dependency(self.temporary_expected_portfolio_update_job)

    async def start(self) -> None:
        """
        Starts the balance updating process
        """
        await self.regular_portfolio_update_job.run()

    async def set_expected_portfolio_update(self, expected_portfolio_update: bool):
        if expected_portfolio_update:
            if not self.temporary_expected_portfolio_update_job.is_started:
                # expected portfolio update is now True: start the associated job as it is not running yet
                self.logger.info(
                    f"Starting temporary expected portfolio update job on {self.channel.exchange_manager.exchange_name}"
                )
                await self.temporary_expected_portfolio_update_job.run()
        elif self.temporary_expected_portfolio_update_job.is_started:
            # expected portfolio update is now False: stop the associated job
            self.logger.info(
                f"Stopping temporary expected portfolio update job on {self.channel.exchange_manager.exchange_name}"
            )
            self.temporary_expected_portfolio_update_job.stop()

    async def _fetch_and_push_portfolio(self):
        try:
            await self.fetch_and_push()
        except errors.FailedRequest as e:
            self.logger.warning(html_util.get_html_summary_if_relevant(e))
            # avoid spamming on disconnected situation
            await asyncio.sleep(constants.FAILED_NETWORK_REQUEST_RETRY_ATTEMPTS)
            # schedule expected portfolio update to fallback on this failed request (after a delay to avoid spamming)
            await self.set_expected_portfolio_update(True)
        except errors.NotSupported:
            self.logger.warning(
                f"{self.channel.exchange_manager.exchange_name} is not supporting updates"
            )
            await self.pause()
        except errors.AuthenticationError as err:
            self.logger.exception(
                err,
                True,
                f"Authentication error when fetching balance: {html_util.get_html_summary_if_relevant(err)}. "
                f"Retrying in the next update cycle"
            )
        except Exception as e:
            self.logger.exception(
                e,
                True,
                f"Failed to update balance : {html_util.get_html_summary_if_relevant(e)}"
            )
            await asyncio.sleep(constants.FAILED_NETWORK_REQUEST_RETRY_ATTEMPTS)
            # schedule expected portfolio update to fallback on this failed request (after a delay to avoid spamming)
            await self.set_expected_portfolio_update(True)

    async def fetch_and_push(self):
        await self.push((await self.fetch_portfolio()))

    async def fetch_portfolio(self):
        """
        Fetch portfolio from exchange
        """
        return await self.channel.exchange_manager.exchange.get_balance()

    async def stop(self) -> None:
        """
        Stop the balance updater
        """
        await super().stop()
        self.regular_portfolio_update_job.stop()
        self.temporary_expected_portfolio_update_job.stop()

    async def resume(self) -> None:
        """
        Resume updater process
        """
        await super().resume()
        if not self.is_running:
            await self.run()


class BalanceProfitabilityUpdater(portfolios_channel.BalanceProfitabilityProducer):
    """
    The Balance Profitability Updater triggers the portfolio profitability calculation
    by subscribing to Mark price and Balance channel updates
    """

    """
    The updater related channel name
    """
    CHANNEL_NAME = constants.BALANCE_PROFITABILITY_CHANNEL

    def __init__(self, channel):
        super().__init__(channel)
        self.logger = logging.get_logger(self.__class__.__name__)
        self.exchange_personal_data = (
            self.channel.exchange_manager.exchange_personal_data
        )
        self.balance_consumer = None
        self.mark_price_consumer = None

    async def start(self) -> None:
        """
        Starts the balance profitability subscribing process
        """
        self.balance_consumer = await exchange_channel.get_chan(
            constants.BALANCE_CHANNEL, self.channel.exchange_manager.id
        ).new_consumer(self.handle_balance_update)
        self.mark_price_consumer = await exchange_channel.get_chan(
            constants.MARK_PRICE_CHANNEL, self.channel.exchange_manager.id
        ).new_consumer(self.handle_mark_price_update)

    async def stop(self) -> None:
        """
        Stop and remove the balance profitability consumers
        """
        await super().stop()
        try:
            await exchange_channel.get_chan(
                constants.BALANCE_CHANNEL, self.channel.exchange_manager.id
            ).remove_consumer(self.balance_consumer)
        except KeyError:
            # balance channel might already be stopped and removed from available channels
            pass
        try:
            await exchange_channel.get_chan(
                constants.MARK_PRICE_CHANNEL, self.channel.exchange_manager.id
            ).remove_consumer(self.mark_price_consumer)
        except KeyError:
            # balance channel might already be stopped and removed from available channels
            pass
        self.balance_consumer = None
        self.mark_price_consumer = None

    async def handle_balance_update(
        self, exchange: str, exchange_id: str, balance: dict
    ) -> None:
        """
        Balance channel consumer callback
        :param exchange: the exchange name
        :param exchange_id: the exchange id
        :param balance: the balance dict
        """
        try:
            await self.exchange_personal_data.handle_portfolio_profitability_update(
                balance=balance, mark_price=None, symbol=None
            )
        except Exception as e:
            self.logger.exception(e, True, f"Fail to handle balance update : {e}")

    async def handle_mark_price_update(
        self,
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        mark_price: decimal.Decimal,
    ) -> None:
        """
        Mark price channel consumer callback
        :param exchange: the exchange name
        :param exchange_id: the exchange id
        :param cryptocurrency: the related currency
        :param symbol: the related symbol
        :param mark_price: the mark price
        """
        try:
            await self.exchange_personal_data.handle_portfolio_profitability_update(
                symbol=symbol, mark_price=mark_price, balance=None
            )
        except Exception as e:
            self.logger.exception(e, True, f"Fail to handle mark price update : {e}")
