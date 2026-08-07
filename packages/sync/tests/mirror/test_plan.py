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

"""Tests for the pure mirror-sync planning step — the Python-side mirror of
octobot_client_ts's mirrorPlan.test.ts, same invariants."""

from octobot_sync.mirror.plan import ExistingMirrorNode, plan_mirror_sync


def test_empty_state_enabling_nothing_plans_nothing():
    plan = plan_mirror_sync(existing_nodes=[], enabled_collection_ids=[])
    assert plan.to_create == []
    assert plan.to_write == []
    assert plan.to_clear == []


def test_first_enable_creates_and_writes_every_enabled_collection():
    plan = plan_mirror_sync(
        existing_nodes=[],
        enabled_collection_ids=["user-accounts", "user-data"],
    )
    assert set(plan.to_create) == {"user-accounts", "user-data"}
    assert set(plan.to_write) == {"user-accounts", "user-data"}
    assert plan.to_clear == []


def test_existing_enabled_node_is_written_but_not_recreated():
    existing = [ExistingMirrorNode(id="n1", type="user-accounts")]
    plan = plan_mirror_sync(existing_nodes=existing, enabled_collection_ids=["user-accounts"])
    assert plan.to_create == []
    assert plan.to_write == ["user-accounts"]
    assert plan.to_clear == []


def test_disabling_a_previously_enabled_collection_clears_it():
    existing = [
        ExistingMirrorNode(id="n1", type="user-accounts"),
        ExistingMirrorNode(id="n2", type="user-data"),
    ]
    plan = plan_mirror_sync(existing_nodes=existing, enabled_collection_ids=["user-accounts"])
    assert plan.to_write == ["user-accounts"]
    assert plan.to_clear == [ExistingMirrorNode(id="n2", type="user-data")]


def test_unknown_collection_ids_are_ignored_entirely():
    plan = plan_mirror_sync(
        existing_nodes=[],
        enabled_collection_ids=["user-accounts", "not-a-real-collection"],
    )
    assert plan.to_create == ["user-accounts"]
    assert plan.to_write == ["user-accounts"]


def test_existing_node_of_an_unknown_type_is_never_cleared_by_this_plan():
    # A node this planner doesn't recognize isn't its business to touch —
    # only known mirror-collection nodes are ever created/written/cleared.
    existing = [ExistingMirrorNode(id="n1", type="some-other-space-node")]
    plan = plan_mirror_sync(existing_nodes=existing, enabled_collection_ids=[])
    assert plan.to_clear == []


def test_enabling_everything_that_already_exists_clears_nothing():
    existing = [
        ExistingMirrorNode(id="n1", type="user-accounts"),
        ExistingMirrorNode(id="n2", type="user-data"),
        ExistingMirrorNode(id="n3", type="user-strategies"),
    ]
    plan = plan_mirror_sync(
        existing_nodes=existing,
        enabled_collection_ids=["user-accounts", "user-data", "user-strategies"],
    )
    assert plan.to_create == []
    assert set(plan.to_write) == {"user-accounts", "user-data", "user-strategies"}
    assert plan.to_clear == []


def test_duplicate_enabled_ids_are_written_once():
    plan = plan_mirror_sync(
        existing_nodes=[], enabled_collection_ids=["user-accounts", "user-accounts"]
    )
    assert plan.to_write == ["user-accounts"]
    assert plan.to_create == ["user-accounts"]
