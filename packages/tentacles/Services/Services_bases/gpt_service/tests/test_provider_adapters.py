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
import logging

import pytest

try:
    from tentacles.Services.Services_bases.gpt_service.provider_adapters import (
        AIProviderAdapter,
        NvidiaAdapter,
        AutoConfigResult,
        auto_configure,
    )
except ImportError:
    from provider_adapters import (  # type: ignore[no-redef]
        AIProviderAdapter,
        NvidiaAdapter,
        AutoConfigResult,
        auto_configure,
    )

import octobot_services.enums as enums

_NIM_KEY_ENV = "NVIDIA_NIM_API_KEY"
_NIM_RPM_ENV = "NVIDIA_NIM_RPM_LIMIT"
_FAKE_KEY = "nvapi-test-key"


def test_rpm_unset_returns_none(monkeypatch):
    monkeypatch.delenv(_NIM_RPM_ENV, raising=False)
    assert NvidiaAdapter().get_rpm_limit() is None


def test_rpm_empty_string_returns_none(monkeypatch):
    monkeypatch.setenv(_NIM_RPM_ENV, "")
    assert NvidiaAdapter().get_rpm_limit() is None


def test_rpm_invalid_int_returns_none_and_warns(monkeypatch, caplog):
    monkeypatch.setenv(_NIM_RPM_ENV, "abc")
    with caplog.at_level(logging.WARNING):
        result = NvidiaAdapter().get_rpm_limit()
    assert result is None
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any(_NIM_RPM_ENV in r.message and "abc" in r.message for r in warnings), (
        f"expected warning mentioning {_NIM_RPM_ENV} and 'abc', got: {[r.message for r in warnings]}"
    )


@pytest.mark.parametrize("raw", ["0", "-5"])
def test_rpm_zero_and_negative_return_none(monkeypatch, raw):
    monkeypatch.setenv(_NIM_RPM_ENV, raw)
    assert NvidiaAdapter().get_rpm_limit() is None


def test_rpm_valid_int_returned(monkeypatch):
    monkeypatch.setenv(_NIM_RPM_ENV, "42")
    assert NvidiaAdapter().get_rpm_limit() == 42


def test_adapter_with_no_rpm_env_field_returns_none(monkeypatch):
    class _NoRPMAdapter(AIProviderAdapter):
        provider = enums.AIProvider.OPENAI
        api_key_env = "OPENAI_SECRET_KEY"
        base_url = "https://api.openai.com/v1"
        rpm_limit_env = None

    monkeypatch.setenv("SOME_RANDOM_ENV", "999")
    assert _NoRPMAdapter().get_rpm_limit() is None


def test_auto_configure_populates_rpm_limit(monkeypatch):
    monkeypatch.setenv(_NIM_KEY_ENV, _FAKE_KEY)
    monkeypatch.setenv(_NIM_RPM_ENV, "10")
    result = auto_configure("default-model", env_model_set=False)
    assert result is not None
    assert result.rpm_limit == 10
    assert result.provider == enums.AIProvider.NVIDIA
    assert result.api_key == _FAKE_KEY
    assert "nvidia" in result.base_url.lower()


def test_auto_configure_no_rpm_env_yields_none(monkeypatch):
    monkeypatch.setenv(_NIM_KEY_ENV, _FAKE_KEY)
    monkeypatch.delenv(_NIM_RPM_ENV, raising=False)
    result = auto_configure("default-model", env_model_set=False)
    assert result is not None
    assert result.rpm_limit is None
    # other fields must still be populated
    assert result.api_key == _FAKE_KEY
    assert result.provider == enums.AIProvider.NVIDIA


def test_auto_configure_no_provider_match_returns_none(monkeypatch):
    monkeypatch.delenv(_NIM_KEY_ENV, raising=False)
    assert auto_configure("default-model", env_model_set=False) is None


def test_auto_configure_log_includes_rpm(monkeypatch, caplog):
    monkeypatch.setenv(_NIM_KEY_ENV, _FAKE_KEY)
    monkeypatch.setenv(_NIM_RPM_ENV, "10")
    with caplog.at_level(logging.INFO):
        auto_configure("default-model", env_model_set=False)
    info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert any("RPM limit: 10" in m for m in info_msgs), (
        f"expected INFO log with 'RPM limit: 10', got: {info_msgs}"
    )


def test_auto_configure_log_omits_rpm_when_unset(monkeypatch, caplog):
    monkeypatch.setenv(_NIM_KEY_ENV, _FAKE_KEY)
    monkeypatch.delenv(_NIM_RPM_ENV, raising=False)
    with caplog.at_level(logging.INFO):
        auto_configure("default-model", env_model_set=False)
    info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert not any("RPM limit" in m for m in info_msgs), (
        f"unexpected 'RPM limit' in log when env unset: {info_msgs}"
    )
