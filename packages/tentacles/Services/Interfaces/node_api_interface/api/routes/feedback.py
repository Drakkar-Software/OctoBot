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

import dataclasses
import typing

import pydantic
from fastapi import APIRouter

import octobot.constants as octobot_constants
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.journey_summary as journey_summary_module
import octobot.community.node_journal.models as journal_models
import octobot.community.node_journal.state as journal_state

router = APIRouter(tags=["feedback"])


class FeedbackUploadRequest(pydantic.BaseModel):
    note: typing.Optional[str] = None
    issue_url: typing.Optional[str] = None
    ui_error_name: typing.Optional[str] = None
    ui_error_route: typing.Optional[str] = None


@dataclasses.dataclass
class FeedbackUploadEnvelope:
    install_id: str
    app_version: str
    event_count: int
    events: list
    ready: bool
    uploaded: bool
    note: typing.Optional[str] = None
    ui_error_name: typing.Optional[str] = None
    ui_error_route: typing.Optional[str] = None


@dataclasses.dataclass
class FeedbackPreview:
    journey_summary: dict
    upload_envelope: FeedbackUploadEnvelope


def _build_feedback_upload_envelope_from_events(
    events: list[journal_models.JournalEventLine],
    *,
    note: str | None = None,
    ui_error_name: str | None = None,
    ui_error_route: str | None = None,
) -> FeedbackUploadEnvelope:
    persisted_state = journal_state.load_persisted_state()
    event_dicts = [event_line.to_storage_dict() for event_line in events]
    return FeedbackUploadEnvelope(
        install_id=persisted_state.install_id,
        app_version=octobot_constants.LONG_VERSION,
        event_count=len(events),
        events=event_dicts,
        ready=True,
        uploaded=False,
        note=note,
        ui_error_name=ui_error_name,
        ui_error_route=ui_error_route,
    )


def _build_feedback_upload_envelope(
    note: str | None = None,
    ui_error_name: str | None = None,
    ui_error_route: str | None = None,
) -> FeedbackUploadEnvelope:
    events = journal_module.read_events()
    return _build_feedback_upload_envelope_from_events(
        events,
        note=note,
        ui_error_name=ui_error_name,
        ui_error_route=ui_error_route,
    )


def _build_feedback_preview() -> FeedbackPreview:
    events = journal_module.read_events()
    journey_summary = journey_summary_module.build_journey_summary(events)
    upload_envelope = _build_feedback_upload_envelope_from_events(events)
    return FeedbackPreview(
        journey_summary=journey_summary.to_dict(),
        upload_envelope=upload_envelope,
    )


def _build_combined_note(note: str | None, issue_url: str | None) -> str | None:
    if note is not None and issue_url is not None:
        return f"{note}\nissue_url: {issue_url}"
    if issue_url is not None:
        return f"issue_url: {issue_url}"
    return note


def export_feedback(body: FeedbackUploadRequest) -> FeedbackUploadEnvelope:
    note = _build_combined_note(body.note, body.issue_url)
    return _build_feedback_upload_envelope(
        note=note,
        ui_error_name=body.ui_error_name,
        ui_error_route=body.ui_error_route,
    )


@router.get("/preview")
def get_preview() -> dict:
    preview = _build_feedback_preview()
    return {
        "journey_summary": preview.journey_summary,
        "upload_envelope": dataclasses.asdict(preview.upload_envelope),
    }


@router.post("/export")
def post_export(body: FeedbackUploadRequest) -> dict:
    envelope = export_feedback(body=body)
    return dataclasses.asdict(envelope)
