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
import contextlib

import tentacles.Services.Interfaces.web_interface.tests as web_interface_tests
import octobot.enums


LOCAL_HOST_URL = "http://localhost:"
# Page checks use web_interface_tests._aihttp_request (one retry on incomplete payload flake).
BROWSE_PAGE_CHECK_MAX_CONCURRENCY = 12
BROWSE_CLIENT_CONNECTION_DRAIN_SECONDS = 0.05


async def _run_page_check_with_semaphore(
    page_check_semaphore: asyncio.Semaphore,
    page_check_coroutine,
):
    async with page_check_semaphore:
        return await page_check_coroutine


async def _gather_all_page_checks(*awaitables):
    page_check_semaphore = asyncio.Semaphore(BROWSE_PAGE_CHECK_MAX_CONCURRENCY)
    results = await asyncio.gather(
        *(
            _run_page_check_with_semaphore(page_check_semaphore, page_check_coroutine)
            for page_check_coroutine in awaitables
        ),
        return_exceptions=True,
    )
    for result in results:
        if isinstance(result, BaseException):
            raise result


async def _yield_for_client_connections_to_close() -> None:
    await asyncio.sleep(BROWSE_CLIENT_CONNECTION_DRAIN_SECONDS)


@contextlib.asynccontextmanager
async def _distribution_test_client_session():
    connector = aiohttp.TCPConnector(
        limit=BROWSE_PAGE_CHECK_MAX_CONCURRENCY,
        force_close=True,
    )
    async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=90)) as session:
        yield session


class AbstractDistributionTester:
    VERBOSE = False  # Set true to print tested urls
    DISTRIBUTION: octobot.enums.OctoBotDistribution = None
    # backlist endpoints expecting additional data
    URL_BLACK_LIST = []
    DOTTED_URLS = []


    async def test_browse_all_pages_no_required_password(self):
        await self._inner_test_browse_all_pages_no_required_password([])


    async def _inner_test_browse_all_pages_no_required_password(self, black_list: list[str]):
        async with web_interface_tests.get_web_interface(False, self.DISTRIBUTION) as web_interface_instance:
            async with _distribution_test_client_session() as session:
                await _gather_all_page_checks(*[
                    web_interface_tests.check_page_no_login_redirect(self._get_rule_url(rule, web_interface_instance.port), session)
                    for rule in self._get_all_native_rules(web_interface_instance, black_list=black_list)
                ])
                await _yield_for_client_connections_to_close()

    async def test_browse_all_pages_required_password_without_login(self):
        await self._inner_test_browse_all_pages_required_password_without_login([])

    async def _inner_test_browse_all_pages_required_password_without_login(self, black_list: list[str]):
        async with web_interface_tests.get_web_interface(True, self.DISTRIBUTION) as web_interface_instance:
            async with _distribution_test_client_session() as session:
                await _gather_all_page_checks(*[
                    web_interface_tests.check_page_login_redirect(self._get_rule_url(rule, web_interface_instance.port), session)
                    for rule in self._get_all_native_rules(web_interface_instance, black_list=black_list)
                ])
                await _yield_for_client_connections_to_close()

    async def test_browse_all_pages_required_password_with_login(self):
        await self.inner_test_browse_all_pages_required_password_with_login([], [])

    async def inner_test_browse_all_pages_required_password_with_login(
            self, auth_black_list: list[str], unauth_black_list: list[str]
    ):
        async with web_interface_tests.get_web_interface(True, self.DISTRIBUTION) as web_interface_instance:
            async with _distribution_test_client_session() as session:
                await web_interface_tests.login_user_on_session(session, web_interface_instance.port)
                # correctly display pages: session is logged in
                await _gather_all_page_checks(*[
                    web_interface_tests.check_page_no_login_redirect(self._get_rule_url(rule, web_interface_instance.port), session)
                    for rule in self._get_all_native_rules(web_interface_instance, black_list=auth_black_list)
                ])
                await _yield_for_client_connections_to_close()
            async with _distribution_test_client_session() as unauthenticated_session:
                # redirect to login page: session is not logged in
                await _gather_all_page_checks(*[
                    web_interface_tests.check_page_login_redirect(self._get_rule_url(rule, web_interface_instance.port), unauthenticated_session)
                    for rule in self._get_all_native_rules(web_interface_instance, black_list=unauth_black_list)
                ])
                await _yield_for_client_connections_to_close()

    async def test_logout(self):
        async with web_interface_tests.get_web_interface(True, self.DISTRIBUTION) as web_interface_instance:
            async with _distribution_test_client_session() as session:
                await web_interface_tests.login_user_on_session(session, web_interface_instance.port)
                await web_interface_tests.check_page_no_login_redirect(
                    f"{LOCAL_HOST_URL}{web_interface_instance.port}/", session
                )
                await web_interface_tests.check_page_login_redirect(
                    f"{LOCAL_HOST_URL}{web_interface_instance.port}/logout",
                    session)
                await web_interface_tests.check_page_login_redirect(
                    f"{LOCAL_HOST_URL}{web_interface_instance.port}/", session
                )

    def _get_all_native_rules(self, web_interface_instance, black_list=None):
        if black_list is None:
            black_list = []
        full_back_list = self.URL_BLACK_LIST + black_list + web_interface_tests.get_plugins_routes(web_interface_instance)
        rules = set(
            rule.rule
            for rule in web_interface_instance.server_instance.url_map.iter_rules()
            if "GET" in rule.methods
            and _has_no_empty_params(rule)
            and rule.rule not in full_back_list
        )
        if self.VERBOSE:
            print(f"{self.__class__.__name__} Tested {len(rules)} rules: {rules}")
        return rules

    def _get_rule_url(self, rule: str, port: int):
        if rule in self.DOTTED_URLS:
            path = rule
        else:
            path = rule.replace('.', '/')
        return f"{LOCAL_HOST_URL}{port}{path}"


def _has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)
