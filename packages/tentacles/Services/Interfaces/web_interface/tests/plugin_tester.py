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
import aiohttp
import asyncio

import tentacles.Services.Interfaces.web_interface.tests as web_interface_tests
import octobot.enums


class AbstractPluginTester:
    DISTRIBUTION: octobot.enums.OctoBotDistribution = octobot.enums.OctoBotDistribution.DEFAULT
    VERBOSE = False  # Set true to print tested urls
    PLUGIN = None
    URL_BLACK_LIST = []

    @classmethod
    def configure_test_profile_storage(cls, profile_storage) -> None:
        pass

    @classmethod
    def configure_test_tentacles_setup(cls, tentacles_setup_config) -> None:
        pass

    @classmethod
    def cleanup_test_tentacles_setup(cls) -> None:
        pass

    def _get_web_interface_context(self, require_password: bool):
        return web_interface_tests.get_web_interface(
            require_password,
            self.DISTRIBUTION,
            configure_profile_storage=self.configure_test_profile_storage,
            configure_tentacles_setup=self.configure_test_tentacles_setup,
            cleanup_tentacles_setup=self.cleanup_test_tentacles_setup,
        )

    async def test_browse_all_pages_no_required_password(self):
        async with self._get_web_interface_context(False) as web_interface_instance:
            async with aiohttp.ClientSession() as session:
                await asyncio.gather(
                    *[web_interface_tests.check_page_no_login_redirect(
                        f"http://localhost:{web_interface_instance.port}{rule.replace('.', '/')}",
                        session)
                        for rule in self._get_rules(web_interface_instance)])

    async def test_browse_all_pages_required_password_without_login(self):
        async with self._get_web_interface_context(True) as web_interface_instance:
            async with aiohttp.ClientSession() as session:
                await asyncio.gather(
                    *[web_interface_tests.check_page_login_redirect(
                        f"http://localhost:{web_interface_instance.port}{rule.replace('.', '/')}",
                        session)
                        for rule in self._get_rules(web_interface_instance)])

    async def test_browse_all_pages_required_password_with_login(self):
        async with self._get_web_interface_context(True) as web_interface_instance:
            async with aiohttp.ClientSession() as session:
                await web_interface_tests.login_user_on_session(session, web_interface_instance.port)
                # correctly display pages: session is logged in
                await asyncio.gather(
                    *[web_interface_tests.check_page_no_login_redirect(
                        f"http://localhost:{web_interface_instance.port}{rule.replace('.', '/')}",
                        session)
                        for rule in self._get_rules(web_interface_instance)])
            async with aiohttp.ClientSession() as unauthenticated_session:
                # redirect to login page: session is not logged in
                await asyncio.gather(
                    *[web_interface_tests.check_page_login_redirect(
                        f"http://localhost:{web_interface_instance.port}{rule.replace('.', '/')}",
                        unauthenticated_session)
                        for rule in self._get_rules(web_interface_instance)])

    def _get_rules(self, web_interface_instance):
        rules = web_interface_tests.get_all_plugin_rules(
            web_interface_instance.server_instance,
            self.PLUGIN,
            self.URL_BLACK_LIST
        )
        if self.VERBOSE:
            print(f"{self.__class__.__name__} Tested {len(rules)} rules: {rules}")
        return rules
