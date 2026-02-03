#  Drakkar-Software OctoBot-Tentacles-Manager
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
import os.path as path
import asyncio

import octobot_commons.logging as logging
import octobot_tentacles_manager.managers as managers
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.util as util


class TentaclesWorker:
    TENTACLES_FETCHING_TIMEOUT = 120

    def __init__(self,
                 reference_tentacles_dir,
                 tentacle_path,
                 bot_installation_path,
                 use_confirm_prompt,
                 aiohttp_session,
                 quite_mode=False,
                 hide_url=False,
                 bot_install_dir=constants.DEFAULT_BOT_INSTALL_DIR):
        self.logger = logging.get_logger(self.__class__.__name__)
        self.quite_mode = quite_mode
        self.hide_url = hide_url
        self.aiohttp_session = aiohttp_session
        self.use_confirm_prompt = use_confirm_prompt

        self.reference_tentacles_root = path.join(reference_tentacles_dir, constants.TENTACLES_ARCHIVE_ROOT) \
            if reference_tentacles_dir is not None else constants.TENTACLES_ARCHIVE_ROOT
        self.bot_installation_path = bot_installation_path
        self.tentacle_path = path.join(bot_installation_path, tentacle_path)
        self.bot_install_dir = bot_install_dir
        self.tentacles_setup_manager = managers.TentaclesSetupManager(self.tentacle_path,
                                                                      self.bot_installation_path,
                                                                      path.join(self.bot_install_dir,
                                                                                constants.DEFAULT_TENTACLE_CONFIG))
        self.tentacles_path_or_url = None
        self.available_tentacles = []

        self.total_steps = 0
        self.progress = 0
        self.errors = []

        self.to_process_tentacle_modules = {}
        self.processed_tentacles_modules = []

        self.fetched_for_requirements_tentacles = []
        self.fetched_for_requirements_tentacles_versions = {}
        self.fetching_requirements = False
        self.requirements_downloading_event = asyncio.Event()

        self.tentacles_setup_config_to_update = None

    def reset_worker(self):
        self.errors = []

        self.to_process_tentacle_modules = {}
        self.processed_tentacles_modules = []

        self.fetched_for_requirements_tentacles = []
        self.fetched_for_requirements_tentacles_versions = {}
        self.fetching_requirements = False
        self.requirements_downloading_event = asyncio.Event()

    def log_summary(self):
        if not self.quite_mode:
            url_identifier = "from ***" if self.hide_url else (
                f"from '{self.tentacles_path_or_url.split('tentacles/')[-1]}'" if self.tentacles_path_or_url else ""
            )
            if self.errors:
                self.logger.info(f" *** Error summary {url_identifier}: ***")
                for error in self.errors:
                    self.logger.error(f"Error when handling tentacle: {error}")
            else:
                self.logger.info(f" *** All tentacles {url_identifier} have been successfully processed ***")

    def register_to_process_tentacles_modules(self, to_process_tentacle):
        self.to_process_tentacle_modules = self._get_version_by_tentacle(to_process_tentacle)

    def register_error_on_missing_tentacles(self, all_tentacles, name_filter):
        if name_filter is not None:
            all_tentacles_names = [tentacle.name for tentacle in all_tentacles]
            missing_tentacles = [tentacle_name
                                 for tentacle_name in name_filter
                                 if tentacle_name not in all_tentacles_names]
            if missing_tentacles:
                self.errors.append(f"Tentacles: {', '.join(missing_tentacles)} can't be found.")

    async def handle_requirements(self, tentacle, callback):
        if tentacle.tentacles_requirements:
            await self._handle_tentacles_requirements(tentacle, callback)
        # TODO: handle python requirements

    async def _handle_tentacles_requirements(self, tentacle, callback):
        missing_requirements = managers.TentacleManager.find_tentacles_missing_requirements(tentacle,
                                                                                            self.to_process_tentacle_modules,
                                                                                            self.available_tentacles)
        if missing_requirements:
            if not self.fetching_requirements:
                self.fetching_requirements = True
                await self._fetch_all_available_tentacles()
            else:
                await asyncio.wait_for(self.requirements_downloading_event.wait(), self.TENTACLES_FETCHING_TIMEOUT)
            await callback(tentacle, missing_requirements)

    def confirm_action(self, action):
        if not self.use_confirm_prompt:
            return True
        else:
            confirmations = ["yes", "y"]
            user_input = input(f"{action} Y/N").lower()
            if user_input in confirmations:
                return True
            else:
                self.logger.info("Action aborted.")
                return False

    async def _fetch_all_available_tentacles(self):
        # try getting it from available tentacles
        await asyncio.gather(*[self._fetch_tentacles_for_requirement(repo)
                               for repo in managers.TentaclesSetupManager.get_available_tentacles_repos()])
        self.requirements_downloading_event.set()

    async def _fetch_tentacles_for_requirement(self, repo):
        await util.fetch_and_extract_tentacles(
            repo, self.tentacles_path_or_url or constants.DEFAULT_TENTACLES_URL,
            self.aiohttp_session, merge_dirs=True, hide_url=self.hide_url
        )
        requirements_tentacles_path = path.join(repo, constants.TENTACLES_ARCHIVE_ROOT)
        self.fetched_for_requirements_tentacles = util.load_tentacle_with_metadata(requirements_tentacles_path)
        self.fetched_for_requirements_tentacles_versions = \
            self._get_version_by_tentacle(self.fetched_for_requirements_tentacles)

    @staticmethod
    def _get_version_by_tentacle(all_tentacles):
        return {tentacle.name: tentacle.version
                for tentacle in all_tentacles}
