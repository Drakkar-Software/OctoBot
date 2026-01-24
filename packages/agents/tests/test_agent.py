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
import pytest

from octobot_agents.agent.channels.ai_agent import AbstractAIAgentChannelProducer
from octobot_agents.agent.channels.agent import AbstractAgentChannel
from octobot_agents.constants import (
    AGENT_DEFAULT_MAX_TOKENS,
    AGENT_DEFAULT_TEMPERATURE,
    AGENT_DEFAULT_MAX_RETRIES,
)


class TestAgentChannel(AbstractAgentChannel):
    """Test channel for testing."""
    pass


class TestAIAgentProducer(AbstractAIAgentChannelProducer):
    """Test agent producer for testing."""
    
    AGENT_CHANNEL = TestAgentChannel
    
    def _get_default_prompt(self) -> str:
        return "You are a test agent."
    
    async def execute(self, input_data, ai_service):
        return {"result": "test"}


def test_agent_name_is_class_name():
    """Test that agent.name is set to the class name."""
    channel = TestAgentChannel()
    agent = TestAIAgentProducer(channel)
    
    assert agent.name == "TestAIAgentProducer"
    assert agent.name == agent.__class__.__name__


def test_agent_default_values():
    """Test that agent uses default values from constants."""
    channel = TestAgentChannel()
    agent = TestAIAgentProducer(channel)
    
    assert agent.max_tokens == AGENT_DEFAULT_MAX_TOKENS
    assert agent.temperature == AGENT_DEFAULT_TEMPERATURE
    assert agent.MAX_RETRIES == AGENT_DEFAULT_MAX_RETRIES


def test_agent_custom_values():
    """Test that agent can override default values."""
    channel = TestAgentChannel()
    agent = TestAIAgentProducer(
        channel,
        max_tokens=5000,
        temperature=0.7,
    )
    
    assert agent.max_tokens == 5000
    assert agent.temperature == 0.7
    assert agent.name == "TestAIAgentProducer"
