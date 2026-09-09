#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
import json
import os

import pytest

import octobot_commons.constants as commons_constants
import octobot_commons.configuration as configuration

import octobot.community.activity_analysis.onboarding_state as onboarding_state_module
import octobot.constants as constants


def _minimal_config(tmp_path, onboarding_state: dict | None = None) -> configuration.Configuration:
    user_root = tmp_path / commons_constants.USER_FOLDER
    user_root.mkdir()
    profiles_path = user_root / commons_constants.PROFILES_FOLDER
    profiles_path.mkdir(parents=True, exist_ok=True)
    config_file_path = user_root / commons_constants.CONFIG_FILE
    metrics_section = {commons_constants.CONFIG_ENABLED_OPTION: True}
    if onboarding_state is not None:
        metrics_section[commons_constants.CONFIG_METRICS_ONBOARDING_STATE] = onboarding_state
    config_data = {
        commons_constants.CONFIG_METRICS: metrics_section,
        constants.CONFIG_COMMUNITY: {},
    }
    with open(config_file_path, "w", encoding="utf-8") as config_file:
        json.dump(config_data, config_file)
    config = configuration.Configuration(
        str(config_file_path),
        str(profiles_path),
        constants.CONFIG_FILE_SCHEMA,
        constants.PROFILE_FILE_SCHEMA,
    )
    config.read(should_raise=False, activate_profile=False)
    return config


class TestOnboardingStateScalarProperties:
    def test_read_write_scalars_propagate_to_storage(self):
        storage: dict = {}
        state = onboarding_state_module.OnboardingState(storage)
        state.onboarding_started_at = 10.0
        state.first_automation_started_at = 20.0
        state.wallet_configured_at = 30.0
        state.onboarding_complete = True
        state.reconciled_from_existing_config = True
        state.reconcile_automations_pending = True
        state.distinct_automation_count = 3
        assert storage["onboarding_started_at"] == 10.0
        assert storage["first_automation_started_at"] == 20.0
        assert storage["wallet_configured_at"] == 30.0
        assert storage["onboarding_complete"] is True
        assert storage["reconciled_from_existing_config"] is True
        assert storage["reconcile_automations_pending"] is True
        assert storage["distinct_automation_count"] == 3


class TestReconcileAutomationsPendingIsSet:
    def test_false_on_empty_storage(self):
        state = onboarding_state_module.OnboardingState({})
        assert state.reconcile_automations_pending_is_set() is False

    def test_true_after_setter(self):
        state = onboarding_state_module.OnboardingState({})
        state.reconcile_automations_pending = False
        assert state.reconcile_automations_pending_is_set() is True


class TestOnboardingStateFromConfig:
    def test_two_from_config_calls_share_backing_object(self, tmp_path):
        config = _minimal_config(tmp_path)
        first_state = onboarding_state_module.OnboardingState.from_config(config)
        second_state = onboarding_state_module.OnboardingState.from_config(config)
        first_state.distinct_automation_count = 2
        assert second_state.distinct_automation_count == 2


class TestOnboardingStateMilestones:
    def test_invalid_milestones_type_raises_on_property_access(self):
        state = onboarding_state_module.OnboardingState({"onboarding_milestones": "invalid"})
        with pytest.raises(ValueError, match="onboarding_milestones must be a mapping"):
            _ = state.milestones

    def test_milestones_or_none_returns_none_for_invalid_type(self):
        state = onboarding_state_module.OnboardingState({"onboarding_milestones": "invalid"})
        assert state.milestones_or_none() is None


class TestOnboardingStateTrackedAutomationIds:
    def test_add_and_get_tracked_automation_ids(self):
        state = onboarding_state_module.OnboardingState({})
        state.add_tracked_automation_id("automation-1")
        state.add_tracked_automation_id("automation-2")
        state.add_tracked_automation_id("automation-1")
        assert state.get_tracked_automation_ids() == {"automation-1", "automation-2"}

    def test_invalid_tracked_automation_ids_list_resets(self):
        state = onboarding_state_module.OnboardingState({"tracked_automation_ids": "invalid"})
        assert state.get_tracked_automation_ids() == set()
        state.add_tracked_automation_id("automation-1")
        assert state.get_tracked_automation_ids() == {"automation-1"}


class TestOnboardingStateRoundTrip:
    def test_mutate_save_and_reload(self, tmp_path):
        config = _minimal_config(tmp_path)
        state = onboarding_state_module.OnboardingState.from_config(config)
        state.onboarding_started_at = 42.0
        state.distinct_automation_count = 1
        state.add_tracked_automation_id("automation-1")
        config.save()
        reloaded_state = onboarding_state_module.OnboardingState.from_config(config)
        assert reloaded_state.onboarding_started_at == 42.0
        assert reloaded_state.distinct_automation_count == 1
        assert reloaded_state.get_tracked_automation_ids() == {"automation-1"}
