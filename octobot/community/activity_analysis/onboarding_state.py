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
import typing

import octobot_commons.configuration as configuration
import octobot_commons.constants as commons_constants


def _load_onboarding_state_storage(config: configuration.Configuration) -> dict[str, typing.Any]:
    metrics_section = config.config.setdefault(commons_constants.CONFIG_METRICS, {})
    if not isinstance(metrics_section, dict):
        raise ValueError(f"{commons_constants.CONFIG_METRICS} must be a mapping in config")
    onboarding_state = metrics_section.setdefault(
        commons_constants.CONFIG_METRICS_ONBOARDING_STATE,
        {},
    )
    if not isinstance(onboarding_state, dict):
        raise ValueError(
            f"{commons_constants.CONFIG_METRICS_ONBOARDING_STATE} must be a mapping in config"
        )
    return onboarding_state


@dataclasses.dataclass
class OnboardingState:
    _storage: dict[str, typing.Any]

    @classmethod
    def from_config(cls, config: configuration.Configuration) -> "OnboardingState":
        return cls(_load_onboarding_state_storage(config))

    @property
    def onboarding_started_at(self) -> typing.Optional[float]:
        started_at = self._storage.get("onboarding_started_at")
        if started_at is None:
            return None
        return float(started_at)

    @onboarding_started_at.setter
    def onboarding_started_at(self, value: typing.Optional[float]) -> None:
        if value is None:
            self._storage.pop("onboarding_started_at", None)
            return
        self._storage["onboarding_started_at"] = value

    @property
    def first_automation_started_at(self) -> typing.Optional[float]:
        started_at = self._storage.get("first_automation_started_at")
        if started_at is None:
            return None
        return float(started_at)

    @first_automation_started_at.setter
    def first_automation_started_at(self, value: typing.Optional[float]) -> None:
        if value is None:
            self._storage.pop("first_automation_started_at", None)
            return
        self._storage["first_automation_started_at"] = value

    @property
    def wallet_configured_at(self) -> typing.Optional[float]:
        configured_at = self._storage.get("wallet_configured_at")
        if configured_at is None:
            return None
        return float(configured_at)

    @wallet_configured_at.setter
    def wallet_configured_at(self, value: typing.Optional[float]) -> None:
        if value is None:
            self._storage.pop("wallet_configured_at", None)
            return
        self._storage["wallet_configured_at"] = value

    @property
    def onboarding_complete(self) -> bool:
        return bool(self._storage.get("onboarding_complete"))

    @onboarding_complete.setter
    def onboarding_complete(self, value: bool) -> None:
        self._storage["onboarding_complete"] = value

    @property
    def reconciled_from_existing_config(self) -> bool:
        return bool(self._storage.get("reconciled_from_existing_config"))

    @reconciled_from_existing_config.setter
    def reconciled_from_existing_config(self, value: bool) -> None:
        self._storage["reconciled_from_existing_config"] = value

    @property
    def reconcile_automations_pending(self) -> bool:
        return bool(self._storage.get("reconcile_automations_pending"))

    @reconcile_automations_pending.setter
    def reconcile_automations_pending(self, value: bool) -> None:
        self._storage["reconcile_automations_pending"] = value

    def reconcile_automations_pending_is_set(self) -> bool:
        return "reconcile_automations_pending" in self._storage

    @property
    def distinct_automation_count(self) -> int:
        return int(self._storage.get("distinct_automation_count", 0))

    @distinct_automation_count.setter
    def distinct_automation_count(self, count: int) -> None:
        self._storage["distinct_automation_count"] = count

    def milestones_or_none(self) -> typing.Optional[dict[str, bool]]:
        milestones = self._storage.setdefault("onboarding_milestones", {})
        if not isinstance(milestones, dict):
            return None
        return milestones

    @property
    def milestones(self) -> dict[str, bool]:
        milestones = self.milestones_or_none()
        if milestones is None:
            raise ValueError("onboarding_milestones must be a mapping in config")
        return milestones

    def tracked_automation_ids_list(self) -> list[str]:
        tracked_ids = self._storage.setdefault("tracked_automation_ids", [])
        if not isinstance(tracked_ids, list):
            tracked_ids = []
            self._storage["tracked_automation_ids"] = tracked_ids
        return tracked_ids

    def add_tracked_automation_id(self, automation_id: str) -> None:
        tracked_ids = self.tracked_automation_ids_list()
        if automation_id not in tracked_ids:
            tracked_ids.append(automation_id)

    def get_tracked_automation_ids(self) -> set[str]:
        tracked_ids = self._storage.setdefault("tracked_automation_ids", [])
        if not isinstance(tracked_ids, list):
            return set()
        return {str(stored_automation_id) for stored_automation_id in tracked_ids if stored_automation_id}
