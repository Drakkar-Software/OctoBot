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

import typing

import pydantic
from fastapi import APIRouter

import octobot.constants
import octobot.community.node_journal as node_journal

try:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import CurrentUser
except ImportError:
    from api.deps import CurrentUser  # type: ignore[no-redef]

router = APIRouter(tags=["feedback"])


class FeedbackUploadEnvelope(pydantic.BaseModel):
    install_id: str
    app_version: str
    onboarding_started_at: float | None
    onboarding_complete: bool
    journey_summary: dict[str, typing.Any]
    events: list[dict[str, typing.Any]]
    uploaded: bool
    ready: bool
    event_count: int
    note: str | None = None


class FeedbackPreviewResponse(pydantic.BaseModel):
    journey_summary: dict[str, typing.Any]
    upload_envelope: FeedbackUploadEnvelope


class FeedbackUploadRequest(pydantic.BaseModel):
    issue_url: str | None = None
    note: str | None = None


def _build_feedback_preview() -> FeedbackPreviewResponse:
    events = node_journal.read_events()
    journey_summary = node_journal.build_journey_summary(events)
    upload_envelope = node_journal.build_upload_envelope(
        events,
        app_version=octobot.constants.LONG_VERSION,
    )
    return FeedbackPreviewResponse(
        journey_summary=journey_summary.to_dict(),
        upload_envelope=FeedbackUploadEnvelope(**upload_envelope.to_dict()),
    )


def _build_feedback_upload_envelope(note: str | None = None) -> FeedbackUploadEnvelope:
    events = node_journal.read_events()
    upload_envelope = node_journal.build_upload_envelope(
        events,
        app_version=octobot.constants.LONG_VERSION,
        note=note,
    )
    return FeedbackUploadEnvelope(**upload_envelope.to_dict())


@router.get("/preview", response_model=FeedbackPreviewResponse)
def get_feedback_preview(current_user: CurrentUser) -> FeedbackPreviewResponse:
    return _build_feedback_preview()


@router.post("/upload", response_model=FeedbackUploadEnvelope)
def upload_feedback(
    current_user: CurrentUser,
    body: FeedbackUploadRequest | None = None,
) -> FeedbackUploadEnvelope:
    note = None
    if body is not None:
        note_parts = []
        if body.note:
            note_parts.append(body.note)
        if body.issue_url:
            note_parts.append(f"issue_url: {body.issue_url}")
        if note_parts:
            note = "\n".join(note_parts)
    return _build_feedback_upload_envelope(note=note)
