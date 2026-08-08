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

"""Tests for the mirror-eligible collection registry — the Python-side
mirror of octobot_client_ts's mirrorCollections.test.ts, same invariants."""

import octobot_sync.mirror.collections as collections_module
from octobot_sync.mirror.collections import (
    MIRROR_COLLECTIONS,
    MirrorCollection,
    MIRROR_SPACE_NAME,
    is_known_mirror_collection,
    mirror_tier_for,
    is_isolated_mirror_collection,
    mirror_visibility_for,
    mirrordoc_path,
)


def test_user_accounts_auth_is_never_a_known_mirror_collection():
    assert is_known_mirror_collection("user-accounts-auth") is False
    assert all(c.id != "user-accounts-auth" for c in MIRROR_COLLECTIONS)


def test_unknown_collection_is_not_known():
    assert is_known_mirror_collection("not-a-real-collection") is False


def test_default_enabled_flags_match_the_ts_twin():
    assert {c.id for c in MIRROR_COLLECTIONS if c.default_enabled} == {
        "user-accounts",
        "user-data",
        "user-strategies",
    }


def test_accounts_trading_is_grantable_but_default_off():
    collection = next(c for c in MIRROR_COLLECTIONS if c.id == "user-accounts-trading")
    assert collection.visibility == "shared"
    assert is_isolated_mirror_collection(collection.id) is True
    assert collection.default_enabled is False


def test_user_settings_is_default_off_and_never_grantable():
    collection = next(c for c in MIRROR_COLLECTIONS if c.id == "user-settings")
    assert collection.visibility == "private"
    assert is_isolated_mirror_collection(collection.id) is False
    assert collection.default_enabled is False


def test_every_collection_carries_the_same_visibility_as_the_ts_twin():
    # Must match mirror/collections.ts's MIRROR_COLLECTIONS exactly — the TS
    # test asserts the same table, and its parity block parses this file.
    assert {c.id: c.visibility for c in MIRROR_COLLECTIONS} == {
        "user-accounts": "shared",
        "user-data": "shared",
        "user-strategies": "shared",
        "user-accounts-trading": "shared",
        "user-settings": "private",
    }


def test_nothing_is_public_today():
    assert [c for c in MIRROR_COLLECTIONS if c.visibility == "public"] == []


def test_unknown_id_resolves_to_the_safe_end_of_the_visibility_enum():
    assert mirror_visibility_for("not-a-real-collection") == "private"


def test_every_known_collection_id_is_unique():
    ids = [c.id for c in MIRROR_COLLECTIONS]
    assert len(ids) == len(set(ids))


def test_shared_collections_are_grantable_via_their_own_keyring():
    # One space now; the TIER is what separates audiences. "shared" -> the
    # isolated tier, so a per-node grant reaches exactly that collection.
    for collection in MIRROR_COLLECTIONS:
        if collection.visibility == "shared":
            assert mirror_tier_for(collection.id) == "isolated"
            assert is_isolated_mirror_collection(collection.id) is True


def test_private_collections_stay_on_the_space_keyring_and_are_never_grantable():
    for collection in MIRROR_COLLECTIONS:
        if collection.visibility == "private":
            assert mirror_tier_for(collection.id) == "private"
            assert is_isolated_mirror_collection(collection.id) is False


def test_public_visibility_routes_to_the_plaintext_tier(monkeypatch):
    # No collection is public yet, so the registry is monkeypatched with one —
    # otherwise the branch that would leak is the one left untested until the
    # day someone publishes a collection.
    monkeypatch.setattr(
        collections_module,
        "MIRROR_COLLECTIONS",
        (*MIRROR_COLLECTIONS, MirrorCollection("user-published", False, "public")),
    )
    assert mirror_visibility_for("user-published") == "public"
    assert mirror_tier_for("user-published") == "public"
    # Public needs no grant at all, so it is not isolated.
    assert is_isolated_mirror_collection("user-published") is False
    assert mirrordoc_path("user-published", "sp-1", "node-1") == "spaces/sp-1/objects/pub/node-1"


def test_an_unknown_id_is_private_and_not_grantable():
    assert mirror_tier_for("nope") == "private"
    assert is_isolated_mirror_collection("nope") is False


def test_one_space_holds_every_collection():
    assert MIRROR_SPACE_NAME == "octobot-mirror"


def test_grantable_collections_are_stored_in_objinv_not_objdoc():
    # objdoc's read roles are space:member with NO cap fallback, so a per-node
    # grant holder could never fetch it. objinv accepts cap:read:objinv, which
    # is exactly what inviteToNode mints. Must match Infra's
    # dk_spaces/collections.py AND octobot_client_ts's mirrorDocPath exactly.
    assert mirrordoc_path("user-accounts", "sp-1", "node-1") == (
        "spaces/sp-1/objects/n/node-1/content"
    )


def test_space_private_collections_stay_on_objdoc():
    assert mirrordoc_path("user-settings", "sp-1", "node-1") == "spaces/sp-1/objects/docs/node-1"
