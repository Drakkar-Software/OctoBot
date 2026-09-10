#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
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

import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.models as journal_models

_ERROR_CATEGORY_FIELD = "error_category"
_ERROR_MESSAGE_FIELD = "error_message"


def sanitize_attribute_value(value: typing.Any) -> typing.Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)):
        return value
    if isinstance(value, list):
        return value
    return str(value)


def sanitize_event_attributes(
    event: journal_events.NodeJournalEvent,
    attributes: journal_models.JournalEventAttributes,
) -> journal_models.JournalEventAttributes:
    sanitized_attributes = {}
    for field_name, value in attributes.to_dict().items():
        if value is None:
            continue
        sanitized_attributes[field_name] = sanitize_attribute_value(value)
    if event in journal_events.FAILURE_EVENTS:
        if _ERROR_CATEGORY_FIELD not in sanitized_attributes:
            return journal_models.JournalEventAttributes.from_dict(sanitized_attributes)
        if _ERROR_MESSAGE_FIELD not in sanitized_attributes:
            sanitized_attributes[_ERROR_MESSAGE_FIELD] = ""
    return journal_models.JournalEventAttributes.from_dict(sanitized_attributes)
