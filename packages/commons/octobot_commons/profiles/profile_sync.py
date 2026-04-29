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

import octobot_commons.constants as commons_constants
import octobot_commons.singleton as singleton
import octobot_commons.logging as logging
import octobot_commons.async_job as async_job
import octobot_commons.authentication as authentication
import octobot_commons.profiles.profile_sharing as profile_sharing


class ProfileSynchronizer(singleton.Singleton):
    """
    Async job to maintain the profile associated to the given configuration up-to-date
    """

    DEFAULT_SYNC_REFRESH_INTERVAL = (
        commons_constants.PROFILE_REFRESH_HOURS_INTERVAL
        * commons_constants.HOURS_TO_SECONDS
    )

    def __init__(self, current_config, on_profile_change):
        super().__init__()
        self.current_config = current_config
        self._on_profile_change = on_profile_change
        self.sync_job = None
        self.sync_interval = self.DEFAULT_SYNC_REFRESH_INTERVAL
        self.logger = logging.get_logger(self.__class__.__name__)

    async def _sync_profile(self):
        if not self.current_config.profile.auto_update:
            self.logger.debug("Skipping profile update check: auto_update is False")
            return
        if not self.current_config.profile.slug:
            self.logger.error(
                "Impossible to check profile updates: profile slug is unset"
            )
            return
        self.logger.info(f"Synchronizing {self.current_config.profile.name} profile")
        if await profile_sharing.update_profile(self.current_config.profile):
            self.logger.info(f"{self.current_config.profile.name} profile updated")
            await self._on_profile_change(self.current_config.profile.name)
        else:
            self.logger.info(
                f"{self.current_config.profile.name} profile already up-to-date"
            )

    async def _should_sync_profiles(self):
        return (
            await authentication.Authenticator.wait_and_check_has_open_source_package()
        )

    async def start(self) -> bool:
        """
        Synch the profile if necessary
        """
        if not await self._should_sync_profiles():
            self.logger.debug("Profile synch loop disabled")
            return False
        self.logger.debug("Starting profile synchronizer")
        self.sync_job = async_job.AsyncJob(
            self._sync_profile,
            first_execution_delay=0,
            execution_interval_delay=self.sync_interval,
        )
        await self.sync_job.run()
        return True

    def stop(self):
        """
        Stop the synchronization loop
        """
        if self.sync_job is not None and not self.sync_job.is_stopped():
            self.logger.debug("Stopping profile synchronizer")
            self.sync_job.stop()


async def start_profile_synchronizer(current_config, on_profile_change):
    """
    Start the clock synchronization loop if possible on this system
    :return: True if the loop has been started
    """
    return await ProfileSynchronizer.instance(current_config, on_profile_change).start()


async def stop_profile_synchronizer():
    """
    Stop the synchronization loop
    """
    return ProfileSynchronizer.instance().stop()
