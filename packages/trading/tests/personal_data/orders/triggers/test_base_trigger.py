#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import pytest
import asyncio

import octobot_trading.personal_data as personal_data


@pytest.fixture
def mock_callback():
    async def callback(*args):
        callback.called = True
        callback.args = args

    callback.called = False
    callback.args = None
    return callback

@pytest.fixture
def trigger(mock_callback):
    return personal_data.BaseTrigger(mock_callback, ("arg1", "arg2"))

def test_init(trigger, mock_callback):
    assert trigger.on_trigger_callback == mock_callback
    assert trigger.on_trigger_callback_args == ("arg1", "arg2")
    assert trigger._trigger_event is None
    assert trigger._trigger_task is None

def test_triggered_when_not_initialized(trigger):
    assert not trigger.triggered()

def test_is_pending_when_not_initialized(trigger):
    assert not trigger.is_pending()

def test_str_representation(trigger):
    expected = f"BaseTrigger({trigger.on_trigger_callback.__name__})"
    assert str(trigger) == expected
    trigger.clear()
    assert str(trigger) == f"BaseTrigger({None})"

@pytest.mark.asyncio
async def test_clear_cancels_pending_task(trigger):
    # Create a mock event and task
    trigger._trigger_event = asyncio.Event()
    trigger._trigger_task = asyncio.create_task(asyncio.sleep(1))

    # Clear should cancel the task and clear attributes
    assert trigger.on_trigger_callback is not None
    assert trigger.on_trigger_callback_args is not None
    trigger.clear()
    assert trigger._trigger_task is None
    assert trigger.on_trigger_callback is None
    assert trigger.on_trigger_callback_args is None

@pytest.mark.asyncio
async def test_call_callback(trigger, mock_callback):
    await trigger.call_callback()
    assert mock_callback.called
    assert mock_callback.args == ("arg1", "arg2")

def test_update_from_other_trigger(trigger):
    with pytest.raises(NotImplementedError):
        trigger.update_from_other_trigger(None)

@pytest.mark.asyncio
async def test_create_watcher_raises_not_implemented(trigger):
    with pytest.raises(NotImplementedError):
        await trigger.create_watcher()

# Test for concrete implementation requirements
def test_create_trigger_event_not_implemented(trigger):
    with pytest.raises(NotImplementedError):
        trigger._create_trigger_event()

@pytest.mark.asyncio
async def test_wait_for_trigger_set(trigger, mock_callback):
    trigger._trigger_event = asyncio.Event()
    wait_task = asyncio.create_task(trigger._wait_for_trigger_set())
    trigger._trigger_event.set()

    # Wait for the callback to be called
    await wait_task
    assert mock_callback.called
    assert mock_callback.args == ("arg1", "arg2")
