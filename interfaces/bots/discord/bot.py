#  Drakkar-Software OctoBot
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

from config import CONFIG_INTERFACES_DISCORD
from interfaces.bots.discord import DISCORD_BOT
from interfaces.bots.interface_bot import InterfaceBot


class DiscordApp(InterfaceBot):
    def __init__(self, config, discord_service):
        super().__init__(config)
        self.discord_service = discord_service

    @DISCORD_BOT.event
    async def on_ready(self):
        self.logger.info(f"DISCORD BOT / Logged in as : {DISCORD_BOT.user.name} & {DISCORD_BOT.user.id}")

    async def command_start(self):
        await self.discord_service.send_message(InterfaceBot.get_command_start())

    async def command_stop(self):
        # TODO add confirmation
        await self.discord_service.send_message("I'm leaving this world...")
        InterfaceBot.set_command_stop()

    async def command_ping(self):
        await self.discord_service.send_message(InterfaceBot.get_command_ping())

    async def command_risk(self, risk):
        try:
            InterfaceBot.set_command_risk(float(risk))
            await self.discord_service.send_message("New risk set successfully.")
        except Exception:
            await self.discord_service.send_message("Failed to set new risk, please provide a number between 0 and 1.")

    async def command_profitability(self):
        await self.discord_service.send_message(InterfaceBot.get_command_profitability())

    async def command_portfolio(self):
        await self.discord_service.send_message(InterfaceBot.get_command_portfolio())

    async def command_open_orders(self):
        await self.discord_service.send_message(InterfaceBot.get_command_open_orders())

    async def command_trades_history(self):
        await self.discord_service.send_message(InterfaceBot.get_command_trades_history())

    # refresh current order lists and portfolios and reload tham from exchanges
    async def command_real_traders_refresh(self):
        result = "Refresh"
        try:
            InterfaceBot.set_command_real_traders_refresh()
            await self.discord_service.send_message(result + " successful")
        except Exception as e:
            await self.discord_service.send_message(f"{result} failure: {e}")

    # Displays my trades, exchanges, evaluators, strategies and trading
    async def command_configuration(self):
        try:
            await self.discord_service.send_message(InterfaceBot.get_command_configuration())
        except Exception:
            await self.discord_service.send_message("I'm unfortunately currently unable to show you my configuration. "
                                                    "Please wait for my initialization to complete.")

    async def command_market_status(self):
        try:
            await self.discord_service.send_message(InterfaceBot.get_command_market_status())
        except Exception:
            await self.discord_service.send_message(
                "I'm unfortunately currently unable to show you my market evaluations, " +
                "please retry in a few seconds.")

    @staticmethod
    def enable(config, is_enabled, associated_config=CONFIG_INTERFACES_DISCORD):
        InterfaceBot.enable(config, is_enabled, associated_config=associated_config)

    @staticmethod
    def is_enabled(config, associated_config=CONFIG_INTERFACES_DISCORD):
        return InterfaceBot.is_enabled(config, associated_config=associated_config)

    @staticmethod
    # TODO implement
    def _is_valid_user(_, associated_config=CONFIG_INTERFACES_DISCORD):
        return InterfaceBot._is_valid_user("", associated_config=associated_config)
