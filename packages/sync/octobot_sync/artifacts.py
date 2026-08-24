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

"""Publish/read dk_spaces' generic ``artifact-events`` collection
(``spaces/{spaceId}/artifact/versions/{version}/events``, delegated encryption,
required author signature).

Domain-agnostic: no "signal"/"strategy" concept here — callers derive their own
``space_id`` via ``artifact_space_id(name)`` (see
``octobot_flow.repositories.community.trading_signals_repository``).

Scope: publish to your own space, plus ``grant_artifact_space_access`` for a
KNOWN identity — no invite-link/discovery flow yet.

Note: ``artifact_space_id`` is a hash, not a ``starfish_spaces`` registry
lookup — the registry write role (``cap:write:spaces``) can never be satisfied
by a plain device cap, so any wallet's first publish would 403 (confirmed
against the real server).

TODO(copy-trading): still missing — (a) how a follower learns a space's
``spaceId``/owner ``userId``, (b) the invite-link path for an unknown identity,
(c) any UI/API surface calling ``grant_artifact_space_access``.
"""

import hashlib
import typing

import starfish_identities
import starfish_keyring
import starfish_protocol.types
import starfish_sdk.types
import starfish_spaces

import octobot_commons.logging as logging


def _artifact_events_name(space_id: str, version: str) -> str:
    return f"spaces/{space_id}/artifact/versions/{version}/events"


def artifact_events_pull_path(space_id: str, version: str) -> str:
    return f"/pull/{_artifact_events_name(space_id, version)}"


def artifact_events_push_path(space_id: str, version: str) -> str:
    return f"/push/{_artifact_events_name(space_id, version)}"


def _logger() -> logging.BotLogger:
    return logging.get_logger("SyncArtifacts")


def artifact_space_id(name: str) -> str:
    """Deterministic space id for ``name`` — pure, no network I/O (see module docstring)."""
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
    return f"sp-{digest[:32]}"


async def ensure_artifact_space(session: starfish_spaces.Session, space_id: str) -> bool:
    """Ensure ``spaces/{space_id}/_access`` exists, TOFU-owned by ``session``.

    Returns True if this call created it, False if it already existed. CAS-retried
    so a concurrent first publish for the same space_id doesn't raise ``ConflictError``.
    """
    created = False

    async def _attempt() -> None:
        nonlocal created
        entry = await starfish_spaces.read_space_access(session.content_client, space_id, session)
        if entry.owner is not None:
            created = False
            return
        await starfish_spaces.write_space_access(
            session.content_client, space_id, session.user_id, [], entry.hash, session, {}
        )
        created = True

    await starfish_spaces.run_cas(_attempt)
    return created


async def ensure_artifact_keyring(session: starfish_spaces.Session, space_id: str) -> None:
    """Create ``space_id``'s space-wide keyring if it doesn't exist yet (owner-only, TOFU)."""
    await starfish_spaces.owner_ensure_space_keyring(
        session.content_client,
        session.keys,
        space_id,
        session.layout,
        starfish_spaces.owner_trusted_adders(session),
    )


async def grant_artifact_space_access(
    session: starfish_spaces.Session, space_id: str, member_user_id: str, member_kem_pub: str
) -> None:
    """Owner-only: add a known identity to the space roster and keyring (no invite link).

    The member reads with their own full session, so this never touches the invite-link
    cap-scope gap noted in the module docstring.
    """
    await starfish_spaces.add_space_member(
        session.content_client, space_id, session.user_id, member_user_id, session
    )
    await starfish_spaces.ensure_space_keyring_recipient(
        session.content_client,
        session.keys,
        space_id,
        {"subKem": member_kem_pub, "userId": member_user_id},
        session.layout,
        starfish_spaces.owner_trusted_adders(session),
    )


async def open_artifact_encryptor(
    session: starfish_spaces.Session,
    space_id: str,
    *,
    owner_ed_pub: typing.Optional[str] = None,
) -> typing.Optional[typing.Any]:
    """Open the delegated encryptor for ``space_id``'s space-wide keyring.

    Returns None ONLY when nothing has been published yet (call ``ensure_artifact_keyring``
    first when publishing) — a missing keyring pulls as HTTP 200 with an empty body, not a
    404. Any other failure (403 not-a-member, 5xx, not-a-recipient) propagates: a caller
    without access must see a real error, not a silent empty read. ``owner_ed_pub`` defaults
    to this session's own identity; a copier must pass the owner's ``session.owner_ed_pub``
    or the trusted-adder set is wrong and every keyring entry gets skipped.

    Pulls/parses the keyring doc directly rather than using
    ``starfish_spaces.open_encryptor``, which hardcodes the recipient to None as of
    starfish-spaces==3.0.0a72 and so never finds a wrapped key.
    """
    layout = session.layout
    resolved_owner_ed_pub = owner_ed_pub if owner_ed_pub is not None else session.owner_ed_pub
    trusted_adders = starfish_identities.compute_owner_trusted_adders(
        resolved_owner_ed_pub, session.keys["edPub"]
    )
    try:
        result = await session.content_client.pull(layout.keyring_pull(space_id))
    except starfish_sdk.types.StarfishHttpError as pull_error:
        if pull_error.status == 404:
            return None
        raise
    if not result.data:
        _logger().debug(f"No artifact keyring published yet for space {space_id!r}")
        return None
    keyring = starfish_keyring.Keyring.from_dict(result.data)
    return starfish_keyring.create_keyring_encryptor(
        keyring, session.keys["kemPub"], session.keys["kemPriv"], trusted_adders=trusted_adders
    )


def seal_artifact_payload(encryptor: typing.Any, payload: dict[str, typing.Any]) -> dict[str, typing.Any]:
    return encryptor.encrypt(payload)


def unseal_artifact_payload(encryptor: typing.Any, item: dict[str, typing.Any]) -> dict[str, typing.Any]:
    return encryptor.decrypt(item["data"])


async def publish_artifact_event(
    session: starfish_spaces.Session,
    space_id: str,
    version: str,
    payload: dict[str, typing.Any],
    ts: typing.Optional[int] = None,
) -> starfish_protocol.types.PushSuccess:
    """Seal ``payload`` under ``space_id``'s keyring and append it to artifact-events."""
    await ensure_artifact_space(session, space_id)
    await ensure_artifact_keyring(session, space_id)
    encryptor = await open_artifact_encryptor(session, space_id)
    if encryptor is None:
        raise starfish_sdk.types.StarfishHttpError(
            0, f"Could not open the artifact keyring encryptor for space {space_id!r}"
        )
    sealed = seal_artifact_payload(encryptor, payload)
    return await session.content_client.append(
        artifact_events_push_path(space_id, version), sealed, ts=ts
    )


async def pull_artifact_events(
    session: starfish_spaces.Session,
    space_id: str,
    version: str,
    last: int,
    *,
    owner_ed_pub: typing.Optional[str] = None,
) -> list[dict[str, typing.Any]]:
    """Pull and unseal up to ``last`` artifact-event elements for ``space_id``.

    ``owner_ed_pub`` — see ``open_artifact_encryptor``; required for a copier reading
    someone else's space. Returns [] only when nothing is published yet; any other
    failure (no access, transport error) propagates.
    """
    encryptor = await open_artifact_encryptor(session, space_id, owner_ed_pub=owner_ed_pub)
    if encryptor is None:
        return []
    items = await session.content_client.pull(
        artifact_events_pull_path(space_id, version), last=last
    )
    if not isinstance(items, list):
        return []
    return [unseal_artifact_payload(encryptor, item) for item in items]
