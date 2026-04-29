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

import flask

import tentacles.Services.Interfaces.web_interface.security as security

_FLASK_APP = flask.Flask(__name__)


def _https_request_at_safe_example():
    return _FLASK_APP.test_request_context(
        "/",
        environ_base={
            "HTTP_HOST": "safe.example",
            "wsgi.url_scheme": "https",
        },
    )


class TestIsSafeRedirectUrl:
    def test_none_is_safe(self):
        assert security.is_safe_redirect_url(None) is True

    def test_empty_and_whitespace_only_are_safe(self):
        assert security.is_safe_redirect_url("") is True
        assert security.is_safe_redirect_url("   ") is True

    def test_non_string_is_unsafe(self):
        assert security.is_safe_redirect_url(42) is False
        assert security.is_safe_redirect_url(["/"]) is False

    def test_single_slash_path_is_unsafe(self):
        with _https_request_at_safe_example():
            assert security.is_safe_redirect_url("/") is False

    def test_double_leading_slash_is_unsafe(self):
        with _https_request_at_safe_example():
            assert security.is_safe_redirect_url("//evil.test/") is False

    def test_absolute_path_same_host_is_safe(self):
        with _https_request_at_safe_example():
            assert security.is_safe_redirect_url("/dashboard") is True
            assert security.is_safe_redirect_url("/a/b") is True

    def test_encoded_tab_octets_are_unsafe(self):
        with _https_request_at_safe_example():
            assert security.is_safe_redirect_url("/%09/%09/%09/evil.test") is False

    def test_full_url_string_is_unsafe(self):
        with _https_request_at_safe_example():
            assert security.is_safe_redirect_url("https://evil.test/") is False

    def test_leading_whitespace_fails_regex_on_raw_target(self):
        """Regex is applied to ``target``, not stripped form (caller may pass unstripped values)."""
        with _https_request_at_safe_example():
            assert security.is_safe_redirect_url(" /ok") is False


class TestRedirectTargetOr:
    def test_returns_default_for_none_non_string_or_blank(self):
        default_path = "/default"
        assert security.redirect_target_or(None, default_path) == default_path
        assert security.redirect_target_or(123, default_path) == default_path
        assert security.redirect_target_or("", default_path) == default_path
        assert security.redirect_target_or("  \t  ", default_path) == default_path

    def test_returns_safe_stripped_target(self):
        with _https_request_at_safe_example():
            assert security.redirect_target_or("/panel", "/home") == "/panel"
            assert security.redirect_target_or("  /panel  ", "/home") == "/panel"

    def test_returns_default_when_redirect_would_be_unsafe(self):
        with _https_request_at_safe_example():
            fallback = "/home"
            assert security.redirect_target_or("//evil", fallback) == fallback
            assert security.redirect_target_or("/", fallback) == fallback


class TestIsSafeUrl:
    def test_delegates_to_same_rules_as_is_safe_redirect_url(self):
        with _https_request_at_safe_example():
            for candidate in (
                None,
                "/safe",
                "/",
                "//bad",
                "https://other/",
            ):
                assert security.is_safe_url(candidate) == security.is_safe_redirect_url(candidate)
