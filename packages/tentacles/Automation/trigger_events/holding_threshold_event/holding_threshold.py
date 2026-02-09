#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import decimal
import typing
import asyncio

import async_channel
import async_channel.enums as channel_enums
import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.configuration as configuration
import octobot_commons.channels_name as channels_name
import octobot_trading.api as trading_api
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.constants as trading_constants
import octobot_trading.util as trading_util
import octobot.automation.bases.abstract_channel_based_trigger_event as abstract_channel_based_trigger_event
import octobot.errors as errors

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges as trading_exchanges


INITIALIZATION_TIMEOUT = 3 * commons_constants.MINUTE_TO_SECONDS


class HoldingThreshold(abstract_channel_based_trigger_event.AbstractChannelBasedTriggerEvent):
    ASSET_NAME = "asset_name"
    AMOUNT = "amount"
    STOP_ON_INFERIOR = "stop_on_inferior"
    EXCHANGE = "exchange"

    def __init__(self):
        super().__init__()
        # config
        self.asset_name: str = None # type: ignore
        self.amount: decimal.Decimal = trading_constants.ZERO
        self.stop_on_inferior: bool = False

    @staticmethod
    def get_description() -> str:
        return (
            "Will trigger when the holdings of the given asset reach the given amount." \
            "Example: a Amount of 0.01 will trigger the automation if your OctoBot holdings of BTC are 0.01 or bellow ."
        )

    def get_user_inputs(
        self, UI: configuration.UserInputFactory, inputs: dict, step_name: str
    ) -> dict:
        return {
            self.EXCHANGE: UI.user_input(
                self.EXCHANGE, commons_enums.UserInputTypes.TEXT, "binance", inputs,
                title="Exchange: exchange to watch price on. Example: binance. Leave empty to enable on all exchanges.",
                parent_input_name=step_name,
            ),
            self.ASSET_NAME: UI.user_input(
                self.ASSET_NAME, commons_enums.UserInputTypes.TEXT, "BTC", inputs,
                title="Asset name: asset to watch holdings on. Example: BTC",
                parent_input_name=step_name,
                other_schema_values={"minLength": 1}
            ),
            self.AMOUNT: UI.user_input(
                self.AMOUNT, commons_enums.UserInputTypes.FLOAT, 0.0, inputs,
                title="Amount: amount of the asset to watch holdings on. Example: 0.01",
                parent_input_name=step_name,
                min_val=0,
                other_schema_values={"exclusiveMinimum": True}
            ),
            self.STOP_ON_INFERIOR: UI.user_input(
                self.STOP_ON_INFERIOR, commons_enums.UserInputTypes.BOOLEAN, True, inputs,
                title="Stop on inferior: stop the automation if the holdings are inferior to the amount",
                parent_input_name=step_name,
            ),
        }

    def apply_config(self, config: dict) -> None:
        self.clear_future()
        self.exchange = config[self.EXCHANGE] or None
        self.asset_name = config[self.ASSET_NAME]
        self.amount = decimal.Decimal(str(config[self.AMOUNT]))
        self.stop_on_inferior = config[self.STOP_ON_INFERIOR]
        if not self.exchange or not self.asset_name or not self.amount:
            raise errors.InvalidAutomationConfigError("Exchange, asset name and amount must be set", self.get_name())

    def _check_threshold(
        self, exchange_manager: "trading_exchanges.ExchangeManager"
    ) -> tuple[bool, typing.Optional[str]]:
        holdings = exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio(self.asset_name)
        if self.stop_on_inferior:
            if holdings.total <= self.amount:
                return True, self._get_reason(holdings)
        else:
            if holdings.total >= self.amount:
                return True, self._get_reason(holdings)
        return False, None

    def _get_reason(self, holdings) -> str:
        return (
            f"Current {self.asset_name} holdings of {float(holdings.total)} are "
            f"{'lower' if self.stop_on_inferior else 'higher'} than the {float(self.amount)} threshold."
        )

    async def register_consumers(self, exchange_id: str) -> list[async_channel.Consumer]:
        return [
            await exchanges_channel.get_chan(
                channels_name.OctoBotTradingChannelsName.BALANCE_CHANNEL.value, exchange_id
            ).new_consumer(
                self.balance_callback,
                priority_level=channel_enums.ChannelConsumerPriorityLevels.HIGH.value,
            )
        ]

    async def balance_callback(self, exchange: str, exchange_id: str, balance):
        if self.should_stop:
            # do not go any further if the action has been stopped
            return
        await self.perform_check(exchange_id)

    async def check_initial_event(self):
        exchange_manager_ids = [trading_api.get_exchange_manager_id(
            trading_api.get_exchange_managers_from_exchange_name(self.exchange)[0]
        )] if self.exchange else trading_api.get_exchange_ids()
        for exchange_id in exchange_manager_ids:
            exchange_manager = trading_api.get_exchange_manager_from_exchange_name_and_id(
                self.exchange, exchange_id
            ) if self.exchange else trading_api.get_exchange_manager_from_exchange_id(exchange_id)
            try:
                await trading_util.wait_for_topic_init(
                    exchange_manager, INITIALIZATION_TIMEOUT, commons_enums.InitializationEventExchangeTopics.BALANCE.value
                )
                await self.perform_check(exchange_id=exchange_id)
            except asyncio.TimeoutError:
                self.logger.error(f"Initialization of balance for {exchange_manager.exchange_name} took more than {INITIALIZATION_TIMEOUT} seconds, skipping initial check")

    async def perform_check(self, exchange_id: str):
        exchange_manager = trading_api.get_exchange_manager_from_exchange_name_and_id(
            self.exchange, exchange_id
        ) if self.exchange else trading_api.get_exchange_manager_from_exchange_id(exchange_id)
        is_threshold_met, reason = self._check_threshold(exchange_manager)
        if is_threshold_met:
            self.trigger(description=reason)
