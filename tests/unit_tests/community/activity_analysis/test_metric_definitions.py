#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
import dataclasses

import octobot_commons.enums as commons_enums

import octobot.community.activity_analysis.metric_definitions as metric_definitions


class TestBaseMetricAttributes:
    def test_to_sentry_dict_sets_event_from_enum_value(self):
        attributes = metric_definitions.NodeWalletConfiguredAttributes()
        sentry_attributes = attributes.to_sentry_dict(bot_id=None)
        assert sentry_attributes["event"] == commons_enums.MetricEvents.NODE_WALLET_CONFIGURED.value

    def test_to_sentry_dict_injects_bot_id_when_provided(self):
        attributes = metric_definitions.ExternalInterfaceConnectedAttributes(source="sync")
        sentry_attributes = attributes.to_sentry_dict(bot_id="bot-id")
        assert sentry_attributes["bot_id"] == "bot-id"

    def test_to_sentry_dict_omits_bot_id_when_none(self):
        attributes = metric_definitions.ExternalInterfaceConnectedAttributes(source="sync")
        sentry_attributes = attributes.to_sentry_dict(bot_id=None)
        assert "bot_id" not in sentry_attributes

    def test_to_sentry_dict_uses_field_names_as_keys(self):
        attributes = metric_definitions.FirstAccountCreateAttemptAttributes(
            is_simulated=True,
            source="debug_api",
        )
        sentry_attributes = attributes.to_sentry_dict(bot_id=None)
        assert set(sentry_attributes.keys()) == {"event", "is_simulated", "source"}

    def test_to_sentry_dict_omits_none_optional_fields(self):
        attributes = metric_definitions.AutomationStartedAttributes(
            automation_count=2,
            octobot_kind=metric_definitions.OctobotKind.MANUAL,
            flow_subtype=None,
        )
        sentry_attributes = attributes.to_sentry_dict(bot_id=None)
        assert "flow_subtype" not in sentry_attributes
        assert dataclasses.asdict(attributes)["flow_subtype"] is None

    def test_to_sentry_dict_coerces_enums_and_bools_to_strings(self):
        attributes = metric_definitions.UserConverted24hReturnAttributes(
            conversion_path=metric_definitions.ConversionPath.POST_ONBOARD,
            return_delay_bucket=metric_definitions.ReturnDelayBucket.HOURS_24_TO_48,
            onboarding_complete=True,
        )
        sentry_attributes = attributes.to_sentry_dict(bot_id=None)
        assert sentry_attributes["conversion_path"] == "post_onboard"
        assert sentry_attributes["return_delay_bucket"] == "24h_48h"
        assert sentry_attributes["onboarding_complete"] == "True"


class TestNodeProcessStartAttributes:
    def test_default_event(self):
        attributes = metric_definitions.NodeProcessStartAttributes(
            wallet_configured=False,
            new_install=True,
            onboarding_complete=False,
            distribution="node",
            version="1.0.0",
        )
        assert attributes.event == commons_enums.MetricEvents.NODE_PROCESS_START


class TestAccountValidatedAttributes:
    def test_serializes_exchange_name(self):
        attributes = metric_definitions.AccountValidatedAttributes(
            is_simulated=False,
            exchange_name="binance",
        )
        sentry_attributes = attributes.to_sentry_dict(bot_id="bot-id")
        assert sentry_attributes["exchange_name"] == "binance"


class TestAutomationStartedAttributes:
    def test_serializes_tentacle_name_string(self):
        attributes = metric_definitions.AutomationStartedAttributes(
            automation_count=1,
            octobot_kind=metric_definitions.OctobotKind.FLOW,
            flow_subtype="GridTradingMode",
        )
        sentry_attributes = attributes.to_sentry_dict(bot_id=None)
        assert sentry_attributes["octobot_kind"] == "flow"
        assert sentry_attributes["flow_subtype"] == "GridTradingMode"

    def test_serializes_flow_subtype_enum(self):
        attributes = metric_definitions.AutomationStartedAttributes(
            automation_count=1,
            octobot_kind=metric_definitions.OctobotKind.FLOW,
            flow_subtype=metric_definitions.FlowSubtype.COPY,
        )
        sentry_attributes = attributes.to_sentry_dict(bot_id=None)
        assert sentry_attributes["flow_subtype"] == "copy"


class TestFirstAutomationStartedAttributes:
    def test_default_event(self):
        attributes = metric_definitions.FirstAutomationStartedAttributes(
            octobot_kind=metric_definitions.OctobotKind.MANUAL,
        )
        assert attributes.event == commons_enums.MetricEvents.FIRST_AUTOMATION_STARTED


class TestStuckNoExternalInterfaceAttributes:
    def test_event_only(self):
        attributes = metric_definitions.StuckNoExternalInterfaceAttributes()
        sentry_attributes = attributes.to_sentry_dict(bot_id=None)
        assert sentry_attributes == {
            "event": commons_enums.MetricEvents.STUCK_NO_EXTERNAL_INTERFACE.value,
        }
