#  This file is part of OctoBot Sync (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

"""Standalone, real-network verification of the dk_spaces artifact publish/pull path.

Not a pytest test — a manual diagnostic script. Walks every step of
octobot_sync.artifacts against a real (or test) dk_spaces sync server and prints a
PASS/FAIL line per step.

Usage:
    python packages/sync/tests/artifacts_check.py \\
        --private-key 0x... \\
        --sync-url https://beta-sync.drakkar.software

Use a throwaway/test private key — never a funded wallet's key on the command
line. --sync-url must be a bare origin (no /sync suffix): build_mirror_session
appends octobot_sync.constants.SYNC_MOUNT_PATH itself, same as every other
caller in this codebase (see octobot_sync/client.py, octobot/constants.py).
"""

import argparse
import asyncio
import sys
import time
import typing

import octobot_sync.mirror.writer as mirror_writer
import octobot_sync.artifacts as artifacts


def _pass(step: str, detail: str = "") -> None:
    print(f"[PASS] {step}" + (f" — {detail}" if detail else ""))


def _fail(step: str, detail: str) -> None:
    print(f"[FAIL] {step} — {detail}")


async def run_check(private_key: str, sync_url: str, artifact_name: str, version: str) -> bool:
    """Run every step in sequence; stop and return False at the first failure."""
    payload = {"artifacts_check": True, "sent_at": time.time()}

    try:
        derived = mirror_writer.derived_identity_for_mirror(private_key)
    except Exception as err:
        _fail("derive identity", str(err))
        return False
    _pass("derive identity", f"user_id={derived['userId']}")

    try:
        session = await mirror_writer.build_mirror_session(derived, sync_url, name="artifacts-check")
    except Exception as err:
        _fail("build session", str(err))
        return False
    _pass("build session", f"namespace={session.namespace} sync_url={sync_url}")

    space_id = artifacts.artifact_space_id(artifact_name)
    try:
        created = await artifacts.ensure_artifact_space(session, space_id)
    except Exception as err:
        _fail("artifact space creation", str(err))
        return False
    _pass(
        "artifact space creation",
        f"{'created new' if created else 'reused existing'} space_id={space_id}",
    )

    try:
        await artifacts.ensure_artifact_keyring(session, space_id)
    except Exception as err:
        _fail("ensure keyring", str(err))
        return False
    _pass("ensure keyring")

    try:
        publish_encryptor = await artifacts.open_artifact_encryptor(session, space_id)
    except Exception as err:
        _fail("open encryptor (publish)", str(err))
        return False
    if publish_encryptor is None:
        _fail("open encryptor (publish)", "returned None — keyring not accessible")
        return False
    _pass("open encryptor (publish)")

    try:
        sealed = artifacts.seal_artifact_payload(publish_encryptor, payload)
    except Exception as err:
        _fail("seal payload", str(err))
        return False
    _pass("seal payload", f"{len(sealed.get('_encrypted', ''))} base64 chars")

    try:
        ts = int(payload["sent_at"] * 1000)
        push_result = await session.content_client.append(
            artifacts.artifact_events_push_path(space_id, version), sealed, ts=ts
        )
    except Exception as err:
        _fail("publish (append)", str(err))
        return False
    _pass("publish (append)", f"hash={push_result.hash} ts={push_result.timestamp}")

    try:
        # A real server round-trip: confirms the space persisted server-side.
        created_again = await artifacts.ensure_artifact_space(session, space_id)
    except Exception as err:
        _fail("resolve space (pull)", str(err))
        return False
    if created_again:
        _fail("resolve space (pull)", "space_access was missing server-side and got re-created")
        return False
    _pass("resolve space (pull)", f"space_id={space_id} confirmed to exist server-side")

    try:
        pull_encryptor = await artifacts.open_artifact_encryptor(session, space_id)
    except Exception as err:
        _fail("open encryptor (pull)", str(err))
        return False
    if pull_encryptor is None:
        _fail("open encryptor (pull)", "returned None — keyring not accessible")
        return False
    _pass("open encryptor (pull)")

    try:
        items = await session.content_client.pull(
            artifacts.artifact_events_pull_path(space_id, version), last=10
        )
    except Exception as err:
        _fail("event fetching (pull)", str(err))
        return False
    if not isinstance(items, list):
        _fail("event fetching (pull)", f"unexpected response type {type(items)}")
        return False
    _pass("event fetching (pull)", f"{len(items)} item(s)")

    try:
        unsealed = [artifacts.unseal_artifact_payload(pull_encryptor, item) for item in items]
    except Exception as err:
        _fail("unseal events", str(err))
        return False
    if payload not in unsealed:
        _fail("unseal + round-trip", "published payload not found among pulled/unsealed items")
        return False
    _pass("unseal + round-trip", "published payload found intact")

    return True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Real-network check of the dk_spaces artifact publish/pull path (artifact space "
            "creation, keyring setup, sealing, publish/append, event fetching) against a "
            "dk_spaces sync server. Prints a PASS/FAIL line per step."
        )
    )
    parser.add_argument(
        "--private-key",
        required=True,
        help="EVM private key (0x-prefixed hex) to derive the test wallet identity from — "
        "use a throwaway/test key, never a funded one",
    )
    parser.add_argument(
        "--sync-url",
        required=True,
        help="Bare sync server origin, e.g. https://beta-sync.drakkar.software "
        "(no /sync suffix — build_mirror_session appends it)",
    )
    parser.add_argument(
        "--artifact-name",
        default=f"artifacts-check-{int(time.time())}",
        help="Artifact space name to publish/pull under (default: a fresh generated name so "
        "repeat runs don't collide)",
    )
    parser.add_argument(
        "--version",
        default="1.0.0",
        help="artifact-events version segment (default: 1.0.0)",
    )
    return parser


async def async_main(argv: typing.Optional[list[str]] = None) -> int:
    """The async core of main(), split out so a caller already inside a running event loop
    (e.g. a pytest-asyncio test) can await it directly instead of nesting an asyncio.run()."""
    args = _build_parser().parse_args(argv)

    print(f"Checking artifact publishing for name={args.artifact_name!r} against {args.sync_url}\n")
    ok = await run_check(args.private_key, args.sync_url, args.artifact_name, args.version)
    print()
    print("RESULT: all steps passed" if ok else "RESULT: FAILED — see the first [FAIL] line above")
    return 0 if ok else 1


def main(argv: typing.Optional[list[str]] = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    sys.exit(main())
