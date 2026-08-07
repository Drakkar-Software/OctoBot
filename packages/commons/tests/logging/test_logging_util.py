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

import octobot_commons.constants as commons_constants
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


def test_error_with_args_formats_message_for_callback(logger, call_wrapper):
    # regression test for https://github.com/Drakkar-Software/OctoBot/issues/3625:
    # the error callback (used for web interface notifications) used to receive
    # the raw, unformatted message instead of the %-substituted one
    logging.BotLogger.register_error_callback(call_wrapper.other_callback)
    logger.error("Blocked edit: edit_type=%s profile=%r reason=%s", "update", "MyProfile", "not allowed")
    call_wrapper.callback_mock.assert_called_once_with(
        None, "Blocked edit: edit_type=update profile='MyProfile' reason=not allowed"
    )


def test_error_with_mismatched_args_falls_back_to_raw_message(logger, call_wrapper):
    # missing/extra args should never raise, just fall back to the raw message
    # note: the underlying stdlib logger.error() call would itself raise a
    # TypeError when formatting mismatched args, unrelated to the formatting
    # safety net under test here (_format_message), so disable the stdlib
    # logger's own formatting by raising its level above ERROR
    logging.BotLogger.register_error_callback(call_wrapper.other_callback)
    logger.logger.setLevel(logging_util.logging.CRITICAL)
    try:
        logger.error("Blocked edit: edit_type=%s reason=%s", "update")
    finally:
        logger.logger.setLevel(logging_util.logging.NOTSET)
    call_wrapper.callback_mock.assert_called_once_with(None, "Blocked edit: edit_type=%s reason=%s")


def test_publish_log_if_necessary_formats_message_with_args(logger):
    with mock.patch.object(logging_util.BotLogger, "_web_interface_publish_log") as publish_mock, \
         mock.patch.object(logging_util, "STORED_LOG_MIN_LEVEL", logging_util.logging.INFO), \
         mock.patch.object(logging_util, "get_global_logger_level", mock.Mock(return_value=logging_util.logging.DEBUG)):
        logger.info("edit_type=%s profile=%r", "update", "MyProfile")
        publish_mock.assert_called_once_with("edit_type=update profile='MyProfile'", logging_util.logging.INFO)


def test_format_message_without_args_returns_message_unchanged():
    assert logging_util.BotLogger._format_message("plain message", ()) == "plain message"


def test_format_message_with_args_substitutes_placeholders():
    assert (
        logging_util.BotLogger._format_message("a=%s b=%r c=%d", ("x", "y", 3))
        == "a=x b='y' c=3"
    )


def test_format_message_with_mismatched_args_returns_raw_message():
    assert logging_util.BotLogger._format_message("a=%s b=%s", ("x",)) == "a=%s b=%s"
    assert logging_util.BotLogger._format_message("a=%d", ("not-a-number",)) == "a=%d"


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


@mock.patch("octobot_commons.logging.logging_util.constants.ALLOW_PRIVATE_DATA_LOGS", True)
def test_get_private_minimized_message_when_allowed_returns_unchanged():
    private_message = "secret-api-key-very-long"
    assert logging_util.get_private_minimized_message_if_necessary(private_message) == private_message


@mock.patch("octobot_commons.logging.logging_util.constants.ALLOW_PRIVATE_DATA_LOGS", True)
def test_get_private_minimized_message_when_allowed_preserves_non_string():
    non_string_payload = {"wallet": "data"}
    assert logging_util.get_private_minimized_message_if_necessary(non_string_payload) is non_string_payload


@mock.patch("octobot_commons.logging.logging_util.constants.ALLOW_PRIVATE_DATA_LOGS", False)
def test_get_private_minimized_message_when_disallowed_truncates_with_placeholder():
    private_message = "abcdefghijklmnop"
    head = private_message[: commons_constants.PRIVATE_MESSAGE_ALLOWED_CHARS_COUNT]
    tail = private_message[-commons_constants.PRIVATE_MESSAGE_ALLOWED_CHARS_COUNT :]
    expected = head + commons_constants.PRIVATE_MESSAGE_PLACEHOLDER + tail
    assert logging_util.get_private_minimized_message_if_necessary(private_message) == expected


@mock.patch("octobot_commons.logging.logging_util.constants.ALLOW_PRIVATE_DATA_LOGS", False)
def test_get_private_minimized_message_when_disallowed_returns_none():
    assert logging_util.get_private_minimized_message_if_necessary(None) is None


@mock.patch("octobot_commons.logging.logging_util.constants.ALLOW_PRIVATE_DATA_LOGS", False)
def test_get_private_minimized_message_when_disallowed_coerces_non_string():
    numeric_token = 123456789
    numeric_str = str(numeric_token)
    head = numeric_str[: commons_constants.PRIVATE_MESSAGE_ALLOWED_CHARS_COUNT]
    tail = numeric_str[-commons_constants.PRIVATE_MESSAGE_ALLOWED_CHARS_COUNT :]
    expected = head + commons_constants.PRIVATE_MESSAGE_PLACEHOLDER + tail
    assert logging_util.get_private_minimized_message_if_necessary(numeric_token) == expected


@mock.patch("octobot_commons.logging.logging_util.constants.ALLOW_PRIVATE_DATA_LOGS", True)
def test_get_private_placeholder_when_allowed_returns_message():
    assert logging_util.get_private_placeholder_if_necessary("sensitive-value") == "sensitive-value"


@mock.patch("octobot_commons.logging.logging_util.constants.ALLOW_PRIVATE_DATA_LOGS", True)
def test_get_private_placeholder_when_allowed_preserves_non_string():
    non_string_payload = object()
    assert logging_util.get_private_placeholder_if_necessary(non_string_payload) is non_string_payload


@mock.patch("octobot_commons.logging.logging_util.constants.ALLOW_PRIVATE_DATA_LOGS", False)
def test_get_private_placeholder_when_disallowed_returns_placeholder_constant():
    assert (
        logging_util.get_private_placeholder_if_necessary("any-content")
        == commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
    )
