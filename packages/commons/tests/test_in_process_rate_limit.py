#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.

import mock
import pytest

import octobot_commons.in_process_rate_limit as in_process_rate_limit

_MONOTONIC_PATCH = "octobot_commons.in_process_rate_limit.time.monotonic"


def _client_ip_policy(**overrides):
    policy_kwargs = {
        "name": "client_ip",
        "max_failures": 3,
        "window_seconds": 60.0,
    }
    policy_kwargs.update(overrides)
    return in_process_rate_limit.FailureWindowPolicy(**policy_kwargs)


def _address_policy(**overrides):
    policy_kwargs = {
        "name": "address",
        "max_failures": 3,
        "window_seconds": 60.0,
        "normalize_key": str.lower,
    }
    policy_kwargs.update(overrides)
    return in_process_rate_limit.FailureWindowPolicy(**policy_kwargs)


def _limiter(*policies):
    return in_process_rate_limit.InProcessFailureRateLimiter(policies)


def _dual_policy_limiter():
    return _limiter(
        _client_ip_policy(max_failures=2),
        _address_policy(max_failures=4),
    )


class TestFailureWindowPolicyNormalizeKey:
    def test_normalizes_keys_per_policy(self):
        limiter = _limiter(
            _address_policy(max_failures=2, window_seconds=60),
        )
        limiter.record_failure(address="0xAbC")
        limiter.record_failure(address="0xabc")
        assert limiter.is_rate_limited(address="0xABC") is True


class TestInProcessFailureRateLimiterInit:
    def test_raises_when_no_policies(self):
        with pytest.raises(ValueError):
            in_process_rate_limit.InProcessFailureRateLimiter(())


class TestInProcessFailureRateLimiterMissingDimension:
    def test_is_rate_limited_raises_key_error(self):
        limiter = _limiter(_client_ip_policy())
        with pytest.raises(KeyError):
            limiter.is_rate_limited()

    def test_record_failure_raises_key_error(self):
        limiter = _limiter(_client_ip_policy())
        with pytest.raises(KeyError):
            limiter.record_failure()

    def test_record_success_raises_key_error(self):
        limiter = _limiter(_client_ip_policy())
        with pytest.raises(KeyError):
            limiter.record_success()

    def test_retry_after_seconds_raises_key_error(self):
        limiter = _limiter(_client_ip_policy())
        with pytest.raises(KeyError):
            limiter.retry_after_seconds()


class TestInProcessFailureRateLimiterRetryAfterSeconds:
    def test_zero_when_not_limited(self):
        limiter = _limiter(_client_ip_policy(max_failures=3))
        assert limiter.retry_after_seconds(client_ip="1.2.3.4") == 0.0
        limiter.record_failure(client_ip="1.2.3.4")
        limiter.record_failure(client_ip="1.2.3.4")
        assert limiter.retry_after_seconds(client_ip="1.2.3.4") == 0.0

    def test_decay_over_window(self):
        limiter = _limiter(_client_ip_policy(max_failures=2, window_seconds=10))
        with mock.patch(_MONOTONIC_PATCH, return_value=0.0):
            limiter.record_failure(client_ip="1.2.3.4")
            limiter.record_failure(client_ip="1.2.3.4")
            assert limiter.retry_after_seconds(client_ip="1.2.3.4") == pytest.approx(10.0)
        with mock.patch(_MONOTONIC_PATCH, return_value=5.0):
            assert limiter.retry_after_seconds(client_ip="1.2.3.4") == pytest.approx(5.0)
        with mock.patch(_MONOTONIC_PATCH, return_value=11.0):
            assert limiter.retry_after_seconds(client_ip="1.2.3.4") == 0.0

    def test_multi_policy_returns_max_remaining(self):
        short_policy = _client_ip_policy(max_failures=2, window_seconds=10)
        long_policy = _address_policy(max_failures=2, window_seconds=100)
        limiter = _limiter(short_policy, long_policy)
        with mock.patch(_MONOTONIC_PATCH, return_value=0.0):
            limiter.record_failure(client_ip="1.2.3.4", address="0xaaa")
            limiter.record_failure(client_ip="1.2.3.4", address="0xaaa")
            remaining = limiter.retry_after_seconds(client_ip="1.2.3.4", address="0xaaa")
        assert remaining == pytest.approx(100.0)

    def test_does_not_reset_buckets(self):
        limiter = _limiter(_client_ip_policy(max_failures=2, window_seconds=10))
        with mock.patch(_MONOTONIC_PATCH, return_value=0.0):
            limiter.record_failure(client_ip="1.2.3.4")
            limiter.record_failure(client_ip="1.2.3.4")
            limiter.retry_after_seconds(client_ip="1.2.3.4")
            assert limiter.is_rate_limited(client_ip="1.2.3.4") is True


class TestInProcessFailureRateLimiterFailureBudget:
    def test_not_limited_below_max_failures(self):
        limiter = _limiter(_client_ip_policy(max_failures=3))
        limiter.record_failure(client_ip="1.2.3.4")
        limiter.record_failure(client_ip="1.2.3.4")
        assert limiter.is_rate_limited(client_ip="1.2.3.4") is False

    def test_limited_at_max_failures(self):
        limiter = _limiter(_client_ip_policy(max_failures=3))
        for _ in range(3):
            limiter.record_failure(client_ip="1.2.3.4")
        assert limiter.is_rate_limited(client_ip="1.2.3.4") is True

    def test_is_rate_limited_does_not_increment(self):
        limiter = _limiter(_client_ip_policy(max_failures=3))
        for _ in range(3):
            limiter.record_failure(client_ip="1.2.3.4")
        assert limiter.is_rate_limited(client_ip="1.2.3.4") is True
        assert limiter.is_rate_limited(client_ip="1.2.3.4") is True


class TestInProcessFailureRateLimiterMultiPolicy:
    def test_limited_when_client_ip_exceeds_budget(self):
        limiter = _dual_policy_limiter()
        limiter.record_failure(client_ip="1.2.3.4", address="0xaaa")
        limiter.record_failure(client_ip="1.2.3.4", address="0xbbb")
        assert limiter.is_rate_limited(client_ip="1.2.3.4", address="0xccc") is True

    def test_limited_when_address_exceeds_budget(self):
        limiter = _dual_policy_limiter()
        address = "0xdef"
        for index in range(4):
            limiter.record_failure(client_ip=f"10.0.0.{index}", address=address)
        assert limiter.is_rate_limited(client_ip="10.0.0.99", address=address) is True

    def test_record_failure_updates_all_policy_stores(self):
        limiter = _dual_policy_limiter()
        limiter.record_failure(client_ip="1.2.3.4", address="0xaaa")
        limiter.record_failure(client_ip="1.2.3.4", address="0xbbb")
        assert limiter.is_rate_limited(client_ip="1.2.3.4", address="0xaaa") is True
        assert limiter.is_rate_limited(client_ip="9.9.9.9", address="0xaaa") is False


class TestInProcessFailureRateLimiterRecordSuccess:
    def test_clears_buckets_for_given_keys(self):
        limiter = _limiter(_client_ip_policy(max_failures=3))
        limiter.record_failure(client_ip="1.2.3.4")
        limiter.record_failure(client_ip="1.2.3.4")
        limiter.record_success(client_ip="1.2.3.4")
        assert limiter.is_rate_limited(client_ip="1.2.3.4") is False
        for _ in range(3):
            limiter.record_failure(client_ip="1.2.3.4")
        assert limiter.is_rate_limited(client_ip="1.2.3.4") is True

    def test_success_on_one_address_does_not_clear_other_address(self):
        limiter = _limiter(_address_policy(max_failures=3))
        limiter.record_failure(address="0xaaa")
        limiter.record_failure(address="0xaaa")
        limiter.record_failure(address="0xbbb")
        limiter.record_failure(address="0xbbb")
        limiter.record_success(address="0xaaa")
        assert limiter.is_rate_limited(address="0xaaa") is False
        assert limiter.is_rate_limited(address="0xbbb") is False
        limiter.record_failure(address="0xbbb")
        assert limiter.is_rate_limited(address="0xbbb") is True


class TestInProcessFailureRateLimiterResetAll:
    def test_clears_every_policy_and_key(self):
        limiter = _limiter(_client_ip_policy(max_failures=2))
        limiter.record_failure(client_ip="1.2.3.4")
        limiter.record_failure(client_ip="1.2.3.4")
        assert limiter.is_rate_limited(client_ip="1.2.3.4") is True
        limiter.reset_all()
        assert limiter.is_rate_limited(client_ip="1.2.3.4") is False


class TestInProcessFailureRateLimiterWindowExpiry:
    def test_is_rate_limited_opens_new_window_after_expiry(self):
        limiter = _limiter(_client_ip_policy(max_failures=2, window_seconds=10))
        with mock.patch(_MONOTONIC_PATCH, return_value=0.0):
            limiter.record_failure(client_ip="1.2.3.4")
            limiter.record_failure(client_ip="1.2.3.4")
            assert limiter.is_rate_limited(client_ip="1.2.3.4") is True
        with mock.patch(_MONOTONIC_PATCH, return_value=11.0):
            assert limiter.is_rate_limited(client_ip="1.2.3.4") is False

    def test_record_failure_starts_new_window_after_expiry(self):
        limiter = _limiter(_client_ip_policy(max_failures=3, window_seconds=10))
        with mock.patch(_MONOTONIC_PATCH, return_value=0.0):
            for _ in range(3):
                limiter.record_failure(client_ip="1.2.3.4")
            assert limiter.is_rate_limited(client_ip="1.2.3.4") is True
        with mock.patch(_MONOTONIC_PATCH, return_value=11.0):
            limiter.record_failure(client_ip="1.2.3.4")
            assert limiter.is_rate_limited(client_ip="1.2.3.4") is False
