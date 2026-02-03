#  Drakkar-Software OctoBot-Commons
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
import mock
import pytest

import octobot_commons.logging as logging
import octobot_commons.logging.logging_util as logging_util


@pytest.fixture
def logger():
    return logging.get_logger("test")


@pytest.fixture
def call_wrapper():
    callback_mock = mock.Mock()

    class Wrapper:
        def __init__(self):
            self.callback_mock = callback_mock

        def other_callback(self, *args, **kwargs):
            callback_mock(*args, **kwargs)
    return Wrapper()


def test_register_error_callback():
    def other_call_back():
        pass
    logging.BotLogger.register_error_callback(logging_util._default_callback)
    assert logging_util._ERROR_CALLBACK is logging_util._default_callback
    logging.BotLogger.register_error_callback(other_call_back)
    assert logging_util._ERROR_CALLBACK is other_call_back


def test_error(logger, call_wrapper):
    logging.BotLogger.register_error_callback(call_wrapper.other_callback)
    logger.error("err")
    call_wrapper.callback_mock.assert_called_once_with(None, "err")
    call_wrapper.callback_mock.reset_mock()

    logger.error("err", skip_post_callback=True)
    call_wrapper.callback_mock.assert_not_called()


def test_exception(logger, call_wrapper):
    logging.BotLogger.register_error_callback(call_wrapper.other_callback)
    err = None
    def raiser():
        def other():
            1/0
        other()
    try:
        raiser()
    except Exception as exc:
        err = exc
        logger.exception(err, True, "error")
    call_wrapper.callback_mock.assert_called_once_with(err, "error")
    call_wrapper.callback_mock.reset_mock()

    logger.exception(err, True, "error", skip_post_callback=True)
    call_wrapper.callback_mock.assert_not_called()
