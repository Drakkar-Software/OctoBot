#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
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

import json
import typing

import pydantic
from fastapi import APIRouter, HTTPException, status

import octobot.community.node_journal as node_journal

router = APIRouter(tags=["journal"])

_MAX_CLIENT_EVENT_ATTRIBUTES_BYTES = 4096


class JournalClientEventRequest(pydantic.BaseModel):
    event: str
    client_instance_id: str | None = None
    attributes: dict[str, typing.Any] | None = None


class JournalClientEventResponse(pydantic.BaseModel):
    event: str
    timestamp: float
    session_id: str
    install_id: str
    app_version: str
    distribution: str
    onboarding_complete: bool
    attributes: dict[str, typing.Any]
    recorded: bool = True


def _validate_client_event(event_name: str) -> node_journal.NodeJournalEvent:
    try:
        parsed_event = node_journal.NodeJournalEvent(event_name)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown journal event: {event_name}",
        ) from error
    if parsed_event not in node_journal.UI_JOURNAL_EVENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event not allowed: {event_name}",
        )
    return parsed_event


def _build_client_event_attributes(body: JournalClientEventRequest) -> dict[str, typing.Any]:
    attributes = dict(body.attributes or {})
    if body.client_instance_id is not None:
        attributes["client_instance_id"] = body.client_instance_id
    if len(json.dumps(attributes, default=str)) > _MAX_CLIENT_EVENT_ATTRIBUTES_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client event attributes payload is too large",
        )
    return attributes


@router.post("/client-event", response_model=JournalClientEventResponse)
def record_journal_client_event(body: JournalClientEventRequest) -> JournalClientEventResponse:
    parsed_event = _validate_client_event(body.event)
    attributes = _build_client_event_attributes(body)
    event_line = node_journal.record(parsed_event, attributes=attributes)
    response_attributes = dict(attributes)
    if event_line.attributes.raw_event_name is not None:
        response_attributes["raw_event_name"] = event_line.attributes.raw_event_name
    event_value = event_line.event.value
    if event_line.recorded is False:
        return JournalClientEventResponse(
            event=event_value,
            timestamp=event_line.timestamp,
            session_id=event_line.session_id,
            install_id=event_line.install_id,
            app_version=event_line.app_version,
            distribution=event_line.distribution,
            onboarding_complete=event_line.onboarding_complete,
            attributes=response_attributes,
            recorded=False,
        )
    return JournalClientEventResponse(
        event=event_value,
        timestamp=event_line.timestamp,
        session_id=event_line.session_id,
        install_id=event_line.install_id,
        app_version=event_line.app_version,
        distribution=event_line.distribution,
        onboarding_complete=event_line.onboarding_complete,
        attributes=response_attributes,
        recorded=True,
    )
