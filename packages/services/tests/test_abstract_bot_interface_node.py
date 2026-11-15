#  Drakkar-Software OctoBot-Services

import datetime

import mock
import pytest

import octobot_protocol.models as protocol_models

import octobot_node.protocol.automations as automations_protocol
import octobot_services.interfaces.bots.abstract_bot_interface as abstract_bot_interface_module
import octobot_services.interfaces.bots.node_command_format as node_command_format

_SAMPLE_TIMESTAMP = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)


def _sample_view(name: str) -> automations_protocol.AutomationReadView:
    automation = protocol_models.AutomationState(
        id="auto-x",
        status=protocol_models.WorkflowStatus.RUNNING,
        metadata=protocol_models.AutomationMetadata(
            name=name,
            description="",
            created_at=_SAMPLE_TIMESTAMP,
            updated_at=_SAMPLE_TIMESTAMP,
        ),
    )
    return automations_protocol.AutomationReadView(
        user_id="wallet-user",
        automation=automation,
        orders=[],
        trades=[],
        fees_by_currency={},
    )


@pytest.mark.asyncio
class TestAbstractBotInterfaceNodeReads:
    async def test_fees_returns_one_message_per_automation(self):
        views = [_sample_view("Alpha"), _sample_view("Beta")]
        with (
            mock.patch.object(
                abstract_bot_interface_module.AbstractBotInterface,
                "is_node_distribution",
                return_value=True,
            ),
            mock.patch.object(
                automations_protocol,
                "get_automation_read_views",
                mock.AsyncMock(return_value=views),
            ),
        ):
            messages = await abstract_bot_interface_module.AbstractBotInterface.get_command_fees()
        assert len(messages) == 2
        assert "Alpha" in messages[0]
        assert "Beta" in messages[1]

    async def test_fees_empty_automations_returns_single_notice(self):
        with (
            mock.patch.object(
                abstract_bot_interface_module.AbstractBotInterface,
                "is_node_distribution",
                return_value=True,
            ),
            mock.patch.object(
                automations_protocol,
                "get_automation_read_views",
                mock.AsyncMock(return_value=[]),
            ),
        ):
            messages = await abstract_bot_interface_module.AbstractBotInterface.get_command_fees()
        assert messages == [node_command_format.NODE_NO_AUTOMATIONS_MESSAGE]


class TestAbstractBotInterfaceNodeRefusals:
    def test_profitability_unavailable_on_node(self):
        with mock.patch.object(
            abstract_bot_interface_module.AbstractBotInterface,
            "is_node_distribution",
            return_value=True,
        ):
            message = abstract_bot_interface_module.AbstractBotInterface.get_command_profitability()
        assert message == node_command_format.NODE_COMMAND_UNAVAILABLE_MESSAGE

    def test_set_command_risk_unavailable_on_node(self):
        with mock.patch.object(
            abstract_bot_interface_module.AbstractBotInterface,
            "is_node_distribution",
            return_value=True,
        ):
            result = abstract_bot_interface_module.AbstractBotInterface.set_command_risk(0.5)
        assert result == node_command_format.NODE_COMMAND_UNAVAILABLE_MESSAGE