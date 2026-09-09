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
import dataclasses
import enum
import typing

import octobot_commons.enums as commons_enums

_EVENT_ATTR = "event"
_BOT_ID_ATTR = "bot_id"


class SentryMetricNames(enum.Enum):
    USAGE = "octobot.usage"
    ONBOARDING_DURATION = "octobot.onboarding.duration"


class OctobotKind(enum.Enum):
    MANUAL = "manual"
    MARKET_MAKING = "market_making"
    FLOW = "flow"


class FlowSubtype(enum.Enum):
    COPY = "copy"
    SIGNAL_BOT = "signal_bot"
    AI_AGENTS = "ai_agents"
    OTHER = "other"


FlowSubtypeValue = FlowSubtype | str


class ReturnDelayBucket(enum.Enum):
    HOURS_24_TO_48 = "24h_48h"
    DAYS_2_TO_7 = "2d_7d"
    DAYS_7_PLUS = "7d_plus"


class ConversionPath(enum.Enum):
    POST_ONBOARD = "post_onboard"
    RECONCILED = "reconciled"


class MetricAttributes(typing.Protocol):
    event: commons_enums.MetricEvents

    def to_sentry_dict(self, bot_id: typing.Optional[str]) -> dict[str, str]:
        ...


def _coerce_sentry_value(value: typing.Any) -> str:
    if isinstance(value, enum.Enum):
        return str(value.value)
    return str(value)


@dataclasses.dataclass(frozen=True, kw_only=True)
class BaseMetricAttributes:
    event: commons_enums.MetricEvents

    def to_sentry_dict(self, bot_id: typing.Optional[str]) -> dict[str, str]:
        attributes: dict[str, str] = {_EVENT_ATTR: self.event.value}
        if bot_id is not None:
            attributes[_BOT_ID_ATTR] = bot_id
        for field in dataclasses.fields(self):
            if field.name == "event":
                continue
            value = getattr(self, field.name)
            if value is None:
                continue
            attributes[field.name] = _coerce_sentry_value(value)
        return attributes


@dataclasses.dataclass(frozen=True, kw_only=True)
class NodeProcessStartAttributes(BaseMetricAttributes):
    wallet_configured: bool
    new_install: bool
    onboarding_complete: bool
    distribution: str
    version: str
    reconciled: typing.Optional[bool] = None
    event: commons_enums.MetricEvents = dataclasses.field(
        default=commons_enums.MetricEvents.NODE_PROCESS_START,
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class AccountValidatedAttributes(BaseMetricAttributes):
    is_simulated: bool
    exchange_name: str
    event: commons_enums.MetricEvents = dataclasses.field(
        default=commons_enums.MetricEvents.ACCOUNT_VALIDATED,
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class AutomationStartedAttributes(BaseMetricAttributes):
    automation_count: int
    octobot_kind: OctobotKind
    flow_subtype: typing.Optional[FlowSubtypeValue] = None
    event: commons_enums.MetricEvents = dataclasses.field(
        default=commons_enums.MetricEvents.AUTOMATION_STARTED,
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class UserConverted24hReturnAttributes(BaseMetricAttributes):
    conversion_path: ConversionPath
    return_delay_bucket: ReturnDelayBucket
    onboarding_complete: bool
    event: commons_enums.MetricEvents = dataclasses.field(
        default=commons_enums.MetricEvents.USER_CONVERTED_24H_RETURN,
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class ExternalInterfaceConnectedAttributes(BaseMetricAttributes):
    source: str
    event: commons_enums.MetricEvents = dataclasses.field(
        default=commons_enums.MetricEvents.EXTERNAL_INTERFACE_CONNECTED,
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class FirstAccountCreateAttemptAttributes(BaseMetricAttributes):
    is_simulated: bool
    source: str
    event: commons_enums.MetricEvents = dataclasses.field(
        default=commons_enums.MetricEvents.FIRST_ACCOUNT_CREATE_ATTEMPT,
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class NodeWalletConfiguredAttributes(BaseMetricAttributes):
    event: commons_enums.MetricEvents = dataclasses.field(
        default=commons_enums.MetricEvents.NODE_WALLET_CONFIGURED,
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class FirstAutomationStartedAttributes(BaseMetricAttributes):
    octobot_kind: OctobotKind
    flow_subtype: typing.Optional[FlowSubtypeValue] = None
    event: commons_enums.MetricEvents = dataclasses.field(
        default=commons_enums.MetricEvents.FIRST_AUTOMATION_STARTED,
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class StuckNoExternalInterfaceAttributes(BaseMetricAttributes):
    event: commons_enums.MetricEvents = dataclasses.field(
        default=commons_enums.MetricEvents.STUCK_NO_EXTERNAL_INTERFACE,
    )
