#  Drakkar-Software OctoBot-Tentacles
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
import time
import typing
import copy

import octobot_services.channel as services_channel
import octobot_services.constants as services_constants
import octobot_services.service_feeds as service_feeds

import octobot_trading.api as trading_api
import octobot_trading.personal_data as personal_data

class ExchangeServiceFeedChannel(services_channel.AbstractServiceFeedChannel):
    pass


class ExchangeProfile:
    DEFAULT_EXCHANGE_PROFILE_REFRESH_TIME = 60

    def __init__(self, profile_id: str, exchange_name: str, exchange_id: str, refresh_time: float = DEFAULT_EXCHANGE_PROFILE_REFRESH_TIME, next_refresh: typing.Optional[float] = None):
        self.profile_id: str = profile_id
        self.exchange_name: str = exchange_name
        self.exchange_id: str = exchange_id
        self.refresh_time: float = refresh_time
        self.next_refresh: float = next_refresh if next_refresh is not None else time.time() + refresh_time

        self.positions: typing.List[personal_data.Position] = []
        self.closed_positions: typing.List[personal_data.Position] = []
        self.trades: typing.List[personal_data.Trade] = []
        self.portfolio: typing.Optional[personal_data.Portfolio] = None
        self.orders: typing.List[personal_data.Order] = []

    def update_next_refresh(self):
        self.next_refresh = time.time() + self.refresh_time

    def update(self, profile_config: dict):
        """
        Update the profile with new configuration values from the profile config dictionary.
        Only updates configurable fields, preserving runtime state.
        """
        refresh_time_changed = False
        
        if "profile_id" in profile_config:
            self.profile_id = profile_config["profile_id"]
        if "exchange_name" in profile_config:
            self.exchange_name = profile_config["exchange_name"]
        if "exchange_id" in profile_config:
            self.exchange_id = profile_config["exchange_id"]
        if "refresh_time" in profile_config:
            self.refresh_time = float(profile_config["refresh_time"])
            refresh_time_changed = True
        
        # Recalculate next_refresh if refresh_time changed
        if refresh_time_changed:
            self.update_next_refresh()

    def __str__(self):
        return f"{self.exchange_id} {self.profile_id}"


class ExchangeServiceFeed(service_feeds.AbstractServiceFeed):
    FEED_CHANNEL = ExchangeServiceFeedChannel
    REQUIRED_SERVICES = False

    DEFAULT_REFRESH_TIME = 10

    def __init__(self, config, main_async_loop, bot_id: str, backtesting=None, importer=None):
        super().__init__(config, main_async_loop, bot_id, backtesting=backtesting, importer=importer)
        self.exchange_profiles: typing.Dict[str, ExchangeProfile] = {}

    def _initialize(self):
        pass

    # merge new config into existing config
    def update_feed_config(self, config, exchange_id: str, exchange_name: str):
        for profile in config[services_constants.CONFIG_EXCHANGE_PROFILES]:
            if profile[services_constants.CONFIG_EXCHANGE_PROFILE_ID] not in self.exchange_profiles.keys():
                self.exchange_profiles[profile[services_constants.CONFIG_EXCHANGE_PROFILE_ID]] = ExchangeProfile(
                    profile_id=profile[services_constants.CONFIG_EXCHANGE_PROFILE_ID],
                    exchange_id=exchange_id,
                    exchange_name=exchange_name
                )
            else:
                self.exchange_profiles[profile[services_constants.CONFIG_EXCHANGE_PROFILE_ID]].update(profile)

    def _something_to_watch(self):
        return bool(self.exchange_profiles.keys())

    def _get_sleep_time_before_next_wakeup(self):
        if not self.exchange_profiles.keys():
            return self.DEFAULT_REFRESH_TIME
        closest_wakeup = min(profile.next_refresh for profile in self.exchange_profiles.values())
        return max(0, closest_wakeup - time.time())

    async def _fetch_exchange_profile(self, profile_id: str) -> bool:
        updated = False
        current_profile = self.exchange_profiles.get(profile_id, None)
        if current_profile is None:
            self.logger.error(f"Exchange profile {profile_id} not found")
            return False

        self.logger.debug(f"Fetching exchange profile on {current_profile.exchange_name} {current_profile.profile_id}")
        exchange_manager = trading_api.get_exchange_manager_from_exchange_name_and_id(current_profile.exchange_name, current_profile.exchange_id)
        current_profile.update_next_refresh()
        exchange_has_positions = True
        if exchange_has_positions:
            current_profile.positions = await exchange_manager.exchange.get_user_positions(current_profile.profile_id)
            updated = True
        else:
            # TODO later: Update portfolio to support SPOT copy trading
            pass

        # TODO Later: should we also fetch orders and trades ?
        return updated

    async def _push_update_and_wait_exchange_profiles(self):
        for profile in self.exchange_profiles.values():
            if time.time() >= profile.next_refresh:
                profile_updated = False
                try:
                    profile_updated = await self._fetch_exchange_profile(profile.profile_id)
                except Exception as e:
                    self.logger.exception(e, True, f"Error when fetching exchange profile: {e}")
                if profile_updated:
                    await self._async_notify_consumers(
                        {
                            services_constants.FEED_METADATA: profile
                        }
                    )

    async def _push_update_and_wait(self):
        if self.exchange_profiles.keys():
            await self._push_update_and_wait_exchange_profiles()
        await asyncio.sleep(self._get_sleep_time_before_next_wakeup())

    async def _update_loop(self):
        while not self.should_stop:
            try:
                await self._push_update_and_wait()
            except Exception as e:
                self.logger.exception(e, True, f"Error when receiving exchange feed: ({e})")
                self.should_stop = True
        return False

    async def _start_service_feed(self):
        try:
            asyncio.create_task(self._update_loop())
        except Exception as e:
            self.logger.exception(e, True, f"Error when initializing exchange feed: {e}")
            return False
        return True
