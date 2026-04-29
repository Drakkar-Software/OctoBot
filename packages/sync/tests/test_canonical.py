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

"""Tests for canonical string building and body hashing."""

import octobot_sync.auth as auth


def test_build_canonical():
    result = auth.build_canonical("GET", "/v1/test", "1234567890", "nonce123", "abc123")
    assert result == "ED25519-OCTOBOT\nGET\n/v1/test\n1234567890\nnonce123\nabc123"


def test_build_canonical_post():
    result = auth.build_canonical("POST", "/v1/push/data", "9999", "n1", "hash1")
    assert result == "ED25519-OCTOBOT\nPOST\n/v1/push/data\n9999\nn1\nhash1"


def test_hash_body_empty():
    h = auth.hash_body("")
    assert len(h) == 64  # SHA-256 hex
    # SHA-256 of empty string
    assert h == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_hash_body_none():
    h = auth.hash_body(None)
    # None should be treated as empty string
    assert h == auth.hash_body("")


def test_hash_body_content():
    h = auth.hash_body('{"key":"value"}')
    assert len(h) == 64
    assert h != auth.hash_body("")
