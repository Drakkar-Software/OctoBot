# pylint: disable=R0913
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
import abc
import functools
import asyncio

import octobot_commons.logging as bot_logging
import octobot_commons.singleton as singleton


class Authenticator(singleton.Singleton):
    """
    Abstract class to be implemented when using authenticated requests
    """

    def __init__(self, use_as_singleton=True):
        self.logger: bot_logging.BotLogger = bot_logging.get_logger(
            self.__class__.__name__
        )
        self.initialized_event: asyncio.Event = None
        self.supports: None
        self.feed_callbacks = {}
        if use_as_singleton:
            # also register this instance for the base Authenticator class in singleton
            self.use_as_singleton_instance()

    # pylint: disable=W0212
    def use_as_singleton_instance(self):
        """
        Update the Authenticator Singleton to use self
        """
        singleton.Singleton._instances[Authenticator] = self
        singleton.Singleton._instances[self.__class__] = self

    @abc.abstractmethod
    async def login(self, username, password, password_token=None):
        """
        Used to trigger a login
        :param username: authentication username
        :param password: authentication password
        :param password_token: (optional) authentication password token
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def logout(self):
        """
        Used to clear a logged in session
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def register(self, username, password):
        """
        Used to create a user account
        :param username: authentication username
        :param password: authentication password
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_aiohttp_session(self):
        """
        Get the aiohttp authenticated session
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def is_logged_in(self):
        """
        :return: True when authenticated
        """
        raise NotImplementedError

    @abc.abstractmethod
    def must_be_authenticated_through_authenticator(self):
        """
        :return: True when this authenticator has to be validated
        """
        raise NotImplementedError

    @abc.abstractmethod
    def ensure_token_validity(self):
        """
        Called before @authenticated methods to ensure authentication
        :return:
        """
        raise NotImplementedError

    async def register_feed_callback(self, topic, callback):
        """
        Registers a feed callback
        """
        raise NotImplementedError

    async def send(self, message, channel_type, identifier=None):
        """
        Sends a message
        """
        raise NotImplementedError

    @abc.abstractmethod
    def is_initialized(self) -> bool:
        """
        Returns True when initialized
        :return:
        """
        raise NotImplementedError

    async def await_initialization(self, timeout):
        """
        Returns when initialized
        :return:
        """
        await asyncio.wait_for(self.initialized_event.wait(), timeout)

    async def update_trades(self, trades: list, exchange_name: str, reset: bool):
        """
        Updates authenticated account trades
        """
        raise NotImplementedError

    async def update_orders(self, orders_by_exchange: dict[str, list]):
        """
        Updates authenticated account orders
        """
        raise NotImplementedError

    async def update_positions(self, positions_by_exchange: dict[str, list]):
        """
        Updates authenticated account positions
        """
        raise NotImplementedError

    async def update_portfolio(
        self,
        current_value: dict,
        initial_value: dict,
        profitability: float,
        unit: str,
        content: dict,
        history: dict,
        price_by_asset: dict,
        reset: bool,
        **kwargs
    ):
        """
        Updates authenticated account portfolio
        """
        raise NotImplementedError

    async def wait_for_private_data_fetch_if_processing(self):
        """
        Returns for private data to be fetched
        """

    def has_open_source_package(self) -> bool:
        """
        :return: True when open source package is available
        """
        raise NotImplementedError

    @staticmethod
    async def wait_and_check_has_open_source_package(raise_on_timeout=False) -> bool:
        """
        Returns for private data to be fetched and return True if package is available
        """
        authenticator = Authenticator.instance()
        try:
            await authenticator.wait_for_private_data_fetch_if_processing()
        except asyncio.TimeoutError:
            if raise_on_timeout:
                raise
        return authenticator.has_open_source_package()


class FailedAuthentication(Exception):
    """
    Raised upon authentication failure
    """


class UnavailableError(Exception):
    """
    Raised upon website availability issues failure
    """


class AuthenticationError(Exception):
    """
    Raised upon authentication technical error, not on login/password issues
    """


class AccountUpdateError(Exception):
    """
    Raised upon account update error
    """


class AuthenticationRequired(Exception):
    """
    Raised when an authentication is required
    """


def authenticated(func):
    """
    Annotation to required authentication for a method call
    :param func:
    :return:
    """

    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        self.ensure_token_validity()
        return func(self, *args, **kwargs)

    return wrapped
