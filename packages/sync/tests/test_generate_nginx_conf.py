#  Drakkar-Software OctoBot-Sync
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

"""Tests for octobot_sync.nginx_conf."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from octobot_sync.util.nginx_conf import generate, storage_path_to_regex, rate_to_nginx

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
COLLECTIONS_PATH = str(FIXTURES_DIR / "collections.json")


def test_static_path_unchanged():
    assert storage_path_to_regex("public/catalog") == "public/catalog"


def test_single_template_replaced():
    assert storage_path_to_regex("users/{identity}") == "users/[^/]+"


def test_multiple_templates_replaced():
    result = storage_path_to_regex("items/{itemId}/feed/{version}")
    assert result == "items/[^/]+/feed/[^/]+"


def test_rate_100_per_60s():
    rate, burst = rate_to_nginx(100, 60_000)
    assert rate == "2r/s"
    assert burst == 50


def test_rate_10_per_60s():
    rate, burst = rate_to_nginx(10, 60_000)
    assert rate == "10r/m"  # 10/60s < 1r/s → use r/m
    assert burst == 5


def test_rate_1_per_60s():
    rate, burst = rate_to_nginx(1, 60_000)
    assert rate == "1r/m"
    assert burst == 1


def test_rate_30_per_30s():
    rate, burst = rate_to_nginx(30, 30_000)
    assert rate == "1r/s"
    assert burst == 15


def test_output_contains_upstream():
    output = generate(COLLECTIONS_PATH, "octobot-sync:3000", 80)
    assert "upstream octobot_sync" in output
    assert "server octobot-sync:3000;" in output


def test_output_contains_cache_path():
    output = generate(COLLECTIONS_PATH, "octobot-sync:3000", 80)
    assert "proxy_cache_path" in output
    assert "sync_cache" in output


def test_listen_port():
    output = generate(COLLECTIONS_PATH, "octobot-sync:3000", 8080)
    assert "listen 8080;" in output


def test_health_endpoint():
    output = generate(COLLECTIONS_PATH, "octobot-sync:3000", 80)
    assert "location = /health" in output


def test_public_pull_only_cached_1h():
    """epsilon-catalog is public + pullOnly → 1h cache."""
    output = generate(COLLECTIONS_PATH, "octobot-sync:3000", 80)
    assert "# epsilon-catalog (public, pull_only)" in output
    assert "proxy_cache_valid 200 1h;" in output


def test_public_writable_cached_30s():
    """delta-feed is public + writable → 30s cache."""
    output = generate(COLLECTIONS_PATH, "octobot-sync:3000", 80)
    assert "# delta-feed (public, writable)" in output
    assert "proxy_cache_valid 200 30s;" in output


def test_private_collections_not_cached():
    """alpha-docs, beta-prefs, gamma-logs, zeta-internal are private → no cache location."""
    output = generate(COLLECTIONS_PATH, "octobot-sync:3000", 80)
    assert "alpha-docs" not in output
    assert "beta-prefs" not in output
    assert "gamma-logs" not in output
    assert "zeta-internal" not in output


def test_cache_status_header():
    output = generate(COLLECTIONS_PATH, "octobot-sync:3000", 80)
    assert "X-Cache-Status" in output


def test_catchall_location():
    output = generate(COLLECTIONS_PATH, "octobot-sync:3000", 80)
    assert "location /v1/" in output


def test_reject_root():
    output = generate(COLLECTIONS_PATH, "octobot-sync:3000", 80)
    assert "return 404;" in output


def test_rate_limit_zones_present():
    """Global rateLimit config → limit_req_zone directives."""
    output = generate(COLLECTIONS_PATH, "octobot-sync:3000", 80)
    assert "limit_req_zone" in output
    assert "zone=sync_global" in output
    assert "zone=sync_strict" in output
    assert "limit_req_status 429;" in output


def test_public_locations_have_global_rate_limit():
    output = generate(COLLECTIONS_PATH, "octobot-sync:3000", 80)
    # delta-feed pull location should have global rate limit
    lines = output.split("\n")
    in_delta = False
    for line in lines:
        if "delta-feed" in line and "writable" in line:
            in_delta = True
        if in_delta and "limit_req zone=sync_global" in line:
            break
        if in_delta and line.strip() == "}":
            pytest.fail("delta-feed pull location missing global rate limit")


def test_rate_limited_push_location():
    """delta-feed has rateLimit: true → strict push location."""
    output = generate(COLLECTIONS_PATH, "octobot-sync:3000", 80)
    assert "# delta-feed (rate limited push)" in output
    assert "/v1/push/items/[^/]+/feed/[^/]+" in output
    assert "zone=sync_strict" in output


def test_pull_only_no_push_rate_limit():
    """epsilon-catalog is pullOnly → no push rate limit location."""
    output = generate(COLLECTIONS_PATH, "octobot-sync:3000", 80)
    assert "epsilon-catalog (rate limited push)" not in output


def test_catchall_has_rate_limit():
    output = generate(COLLECTIONS_PATH, "octobot-sync:3000", 80)
    lines = output.split("\n")
    in_catchall = False
    for line in lines:
        if "Catch-all" in line:
            in_catchall = True
        if in_catchall and "limit_req zone=sync_global" in line:
            break
        if in_catchall and line.strip() == "}":
            pytest.fail("Catch-all location missing rate limit")


def test_no_rate_limit_config():
    """When global rateLimit is absent, no rate limiting directives."""
    config = {
        "version": 1,
        "collections": [
            {
                "name": "public-col",
                "storagePath": "public/data",
                "readRoles": ["public"],
                "writeRoles": ["admin"],
                "encryption": "none",
                "maxBodyBytes": 65536,
            }
        ],
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(config, f)
        f.flush()
        try:
            output = generate(f.name, "octobot-sync:3000", 80)
        finally:
            os.unlink(f.name)

    assert "limit_req_zone" not in output
    assert "limit_req" not in output
    assert "public-col" in output
