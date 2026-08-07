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
    DEFAULT_MIRROR_COLLECTIONS,
    MIRROR_COLLECTIONS,
    MirrorCollection,
    MIRROR_SPACE_PRIVATE_NAME,
    MIRROR_SPACE_PUBLIC_NAME,
    MIRROR_SPACE_SHARED_NAME,
    is_known_mirror_collection,
    is_public_mirror_collection,
    is_third_party_eligible,
    mirror_space_name_for,
    mirror_visibility_for,
    mirrordoc_path,
    mirrordoc_pull_path,
    mirrordoc_push_path,
)


def test_user_accounts_auth_is_never_a_known_mirror_collection():
    assert is_known_mirror_collection("user-accounts-auth") is False
    assert all(c.id != "user-accounts-auth" for c in MIRROR_COLLECTIONS)


def test_user_accounts_auth_is_never_third_party_eligible():
    assert is_third_party_eligible("user-accounts-auth") is False


def test_unknown_collection_is_not_known_or_eligible():
    assert is_known_mirror_collection("not-a-real-collection") is False
    assert is_third_party_eligible("not-a-real-collection") is False


def test_default_mirror_collections_are_exactly_the_default_enabled_ones():
    assert set(DEFAULT_MIRROR_COLLECTIONS) == {
        c.id for c in MIRROR_COLLECTIONS if c.default_enabled
    }
    assert set(DEFAULT_MIRROR_COLLECTIONS) == {
        "user-accounts",
        "user-data",
        "user-strategies",
    }


def test_accounts_trading_is_third_party_eligible_but_default_off():
    collection = next(c for c in MIRROR_COLLECTIONS if c.id == "user-accounts-trading")
    assert collection.visibility == "shared"
    assert is_third_party_eligible(collection.id) is True
    assert collection.default_enabled is False


def test_user_settings_is_default_off_and_not_third_party_eligible():
    collection = next(c for c in MIRROR_COLLECTIONS if c.id == "user-settings")
    assert collection.visibility == "private"
    assert is_third_party_eligible(collection.id) is False
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
    assert all(is_public_mirror_collection(c.id) is False for c in MIRROR_COLLECTIONS)


def test_unknown_id_resolves_to_the_safe_end_of_the_visibility_enum():
    assert mirror_visibility_for("not-a-real-collection") == "private"
    assert is_public_mirror_collection("not-a-real-collection") is False


def test_third_party_eligibility_is_derived_from_visibility():
    for collection in MIRROR_COLLECTIONS:
        assert is_third_party_eligible(collection.id) is (collection.visibility != "private")


def test_every_known_collection_id_is_unique():
    ids = [c.id for c in MIRROR_COLLECTIONS]
    assert len(ids) == len(set(ids))


def test_shared_collections_route_to_the_shared_space():
    for collection in MIRROR_COLLECTIONS:
        if collection.visibility == "shared":
            assert mirror_space_name_for(collection.id) == MIRROR_SPACE_SHARED_NAME


def test_private_collections_route_to_the_private_space():
    for collection in MIRROR_COLLECTIONS:
        if collection.visibility == "private":
            assert mirror_space_name_for(collection.id) == MIRROR_SPACE_PRIVATE_NAME


def test_public_visibility_routes_to_a_third_space(monkeypatch):
    # Infra's `_project_objindex_public` keys the world-readable object
    # projection BY SPACE ID, so a public node in the shared space would hand
    # anonymous readers the id of the space read-only grants are minted
    # against. No collection is public yet, so the registry is monkeypatched
    # with one — otherwise the branch that would leak is the one left untested
    # until the day someone publishes a collection.
    monkeypatch.setattr(
        collections_module,
        "MIRROR_COLLECTIONS",
        (*MIRROR_COLLECTIONS, MirrorCollection("user-published", False, "public")),
    )
    assert mirror_visibility_for("user-published") == "public"
    assert is_public_mirror_collection("user-published") is True
    # Public content is still third-party eligible: a grant holder may read it.
    assert is_third_party_eligible("user-published") is True
    assert mirror_space_name_for("user-published") == MIRROR_SPACE_PUBLIC_NAME
    assert mirror_space_name_for("user-published") not in (
        MIRROR_SPACE_SHARED_NAME,
        MIRROR_SPACE_PRIVATE_NAME,
    )


def test_the_three_space_names_are_pairwise_distinct():
    names = (MIRROR_SPACE_SHARED_NAME, MIRROR_SPACE_PRIVATE_NAME, MIRROR_SPACE_PUBLIC_NAME)
    assert len(set(names)) == len(names)


def test_mirror_doc_path_resolves_to_objdoc():
    # Must match Infra's dk_spaces/collections.py `objdoc` storage_path AND
    # octobot_client_ts's mirror/collections.ts::mirrorDocPath exactly (for the
    # private/shared visibilities — this writer never creates public nodes) — a
    # mismatch means the node writes somewhere the server does not register.
    #
    # objdoc is the canonical content location for a node created
    # access:"space", enc:True, which is how the writer creates them. A
    # dedicated `mirrordoc` collection briefly existed purely for a bigger body
    # limit; objdoc is now 10 MiB and that clone is gone. This asserts it does
    # not drift back.
    assert mirrordoc_path("sp-1", "node-1") == "spaces/sp-1/objects/docs/node-1"
    assert "objects/mirror/" not in mirrordoc_path("sp-1", "node-1")


def test_mirror_doc_pull_and_push_paths_are_prefixed():
    assert mirrordoc_pull_path("sp-1", "node-1") == "/pull/spaces/sp-1/objects/docs/node-1"
    assert mirrordoc_push_path("sp-1", "node-1") == "/push/spaces/sp-1/objects/docs/node-1"
