#  Drakkar-Software OctoBot-Commons
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
import time
import mock
import pytest
import asyncio

import octobot_commons.errors
import octobot_commons.signals as signals
import octobot_commons.signals.signals_emitter as signals_emitter
import octobot_commons.asyncio_tools as asyncio_tools

from tests.signals import signal_builder_wrapper


@pytest.fixture
def publisher():
    try:
        yield signals.SignalPublisher.instance()
    finally:
        signals.SignalPublisher.instance()._timeout_watcher_tasks = {}
        signals.SignalPublisher.instance()._signal_builder_wrappers = {}


def test_get_signal_bundle_builder(publisher, signal_builder_wrapper):
    with pytest.raises(octobot_commons.errors.MissingSignalBuilder):
        signals.SignalPublisher.instance().get_signal_bundle_builder("")
    signals.SignalPublisher.instance()._signal_builder_wrappers["Hi"] = signal_builder_wrapper
    with pytest.raises(octobot_commons.errors.MissingSignalBuilder):
        signals.SignalPublisher.instance().get_signal_bundle_builder("")
    assert signals.SignalPublisher.instance().get_signal_bundle_builder("Hi") \
           is signal_builder_wrapper.signal_bundle_builder


@pytest.mark.asyncio
async def test_remote_signal_bundle_builder(publisher, signal_builder_wrapper):
    async with signals.SignalPublisher.instance().remote_signal_bundle_builder(
            "wkey", "widentifier"
    ) as builder:
        assert isinstance(builder, signals.SignalPublisher.DEFAULT_SIGNAL_BUILDER_CLASS)
        assert "wkey" in signals.SignalPublisher.instance()._signal_builder_wrappers
        assert "wkey" not in signals.SignalPublisher.instance()._timeout_watcher_tasks
    assert "wkey" not in signals.SignalPublisher.instance()._signal_builder_wrappers
    assert "wkey" not in signals.SignalPublisher.instance()._timeout_watcher_tasks

    class OtherSignalBuilder(signals.SignalPublisher.DEFAULT_SIGNAL_BUILDER_CLASS):
        def __init__(self, identifier: str, other_arg):
            super().__init__(identifier)
            self.other_arg = other_arg
    with mock.patch.object(signals.SignalPublisher.instance(), "_emit_signal_if_necessary", mock.AsyncMock()) as \
         _emit_signal_if_necessary_mock:
        with pytest.raises(TypeError):
            # missing builder custom arg
            async with signals.SignalPublisher.instance().remote_signal_bundle_builder(
                    "wkey", "widentifier", timeout=1, signal_builder_class=OtherSignalBuilder
            ):
                pass
            _emit_signal_if_necessary_mock.assert_not_called()
            assert "wkey" not in signals.SignalPublisher.instance()._signal_builder_wrappers
            assert "wkey" not in signals.SignalPublisher.instance()._timeout_watcher_tasks
        with pytest.raises(RuntimeError):
            async with signals.SignalPublisher.instance().remote_signal_bundle_builder(
                    "wkey", "widentifier", timeout=1, signal_builder_class=OtherSignalBuilder, builder_args=("other", )
            ) as builder:
                assert isinstance(builder, OtherSignalBuilder)
                assert builder.other_arg == "other"
                assert "wkey" in signals.SignalPublisher.instance()._signal_builder_wrappers
                assert "wkey" in signals.SignalPublisher.instance()._timeout_watcher_tasks
                raise RuntimeError
            _emit_signal_if_necessary_mock.assert_not_called()
            assert "wkey" not in signals.SignalPublisher.instance()._signal_builder_wrappers
            assert "wkey" not in signals.SignalPublisher.instance()._timeout_watcher_tasks

        async with signals.SignalPublisher.instance().remote_signal_bundle_builder(
                "wkey", "widentifier", timeout=1, signal_builder_class=OtherSignalBuilder, builder_args=("other", )
        ) as builder:
            assert isinstance(builder, OtherSignalBuilder)
            assert "wkey" in signals.SignalPublisher.instance()._signal_builder_wrappers
            assert "wkey" in signals.SignalPublisher.instance()._timeout_watcher_tasks
            wrapper = signals.SignalPublisher.instance()._signal_builder_wrappers["wkey"]
        _emit_signal_if_necessary_mock.assert_called_once_with(wrapper)
        assert "wkey" not in signals.SignalPublisher.instance()._signal_builder_wrappers
        assert "wkey" not in signals.SignalPublisher.instance()._timeout_watcher_tasks


def test_stop(publisher):
    signals.SignalPublisher.instance().stop()
    assert not signals.SignalPublisher.instance()._timeout_watcher_tasks
    assert not signals.SignalPublisher.instance()._signal_builder_wrappers

    cancel_mock_1 = mock.Mock()
    cancel_mock_2 = mock.Mock()
    signals.SignalPublisher.instance()._timeout_watcher_tasks = {
        "h": mock.Mock(cancel=cancel_mock_1),
        "i": mock.Mock(cancel=cancel_mock_2)
    }
    signals.SignalPublisher.instance()._signal_builder_wrappers = {"g": 0, "i": "fdfs"}
    signals.SignalPublisher.instance().stop()
    cancel_mock_1.assert_called_once()
    cancel_mock_2.assert_called_once()
    assert not signals.SignalPublisher.instance()._timeout_watcher_tasks
    assert not signals.SignalPublisher.instance()._signal_builder_wrappers


def test_create_or_get_signal_builder_wrapper(publisher):
    with pytest.raises(TypeError):
        signals.SignalPublisher.instance()._create_or_get_signal_builder_wrapper(
            "key2", "id", 1, signals.SignalPublisher.DEFAULT_SIGNAL_BUILDER_CLASS, ("unexpected_args", )
        )
    wrapper_1 = signals.SignalPublisher.instance()._create_or_get_signal_builder_wrapper(
        "key", "id", 1, signals.SignalPublisher.DEFAULT_SIGNAL_BUILDER_CLASS, None
    )
    assert signals.SignalPublisher.instance()._create_or_get_signal_builder_wrapper(
        "key", "id", 1, signals.SignalPublisher.DEFAULT_SIGNAL_BUILDER_CLASS, None
    ) is wrapper_1

    wrapper_2 = signals.SignalPublisher.instance()._create_or_get_signal_builder_wrapper(
        "key2", "id", 1, signals.SignalPublisher.DEFAULT_SIGNAL_BUILDER_CLASS, None
    )
    assert wrapper_1 != wrapper_2
    assert "key" in signals.SignalPublisher.instance()._signal_builder_wrappers
    assert "key2" in signals.SignalPublisher.instance()._signal_builder_wrappers


@pytest.mark.asyncio
async def test_emit_signal_if_necessary(publisher, signal_builder_wrapper):
    with mock.patch.object(signals_emitter, "emit_signal_bundle", mock.AsyncMock()) as emit_signal_bundle_mock:
        signal_builder_mock = mock.Mock(
            is_empty=mock.Mock(return_value=True), build=mock.Mock(return_value="build_res"), reset=mock.Mock()
        )
        signal_builder_wrapper.signal_bundle_builder = signal_builder_mock
        await signals.SignalPublisher.instance()._emit_signal_if_necessary(signal_builder_wrapper)
        signal_builder_mock.is_empty.assert_called_once()
        signal_builder_mock.build.assert_not_called()
        signal_builder_mock.reset.assert_not_called()
        emit_signal_bundle_mock.assert_not_called()

        signal_builder_mock.is_empty.reset_mock()
        signal_builder_mock.is_empty.return_value = False
        await signals.SignalPublisher.instance()._emit_signal_if_necessary(signal_builder_wrapper)
        signal_builder_mock.is_empty.assert_called_once()
        signal_builder_mock.build.assert_called_once()
        signal_builder_mock.reset.assert_called_once()
        emit_signal_bundle_mock.assert_called_once_with("build_res")


@pytest.mark.asyncio
async def test_schedule_signal_auto_emit(publisher, signal_builder_wrapper):
    with mock.patch.object(signals.SignalPublisher.instance(), "_emit_signal_if_necessary", mock.AsyncMock()) as \
         _emit_signal_if_necessary_mock:
        await signals.SignalPublisher.instance()._schedule_signal_auto_emit("key", 0.001)
        _emit_signal_if_necessary_mock.assert_not_called()

        signal_builder_wrapper.signal_emit_time = time.time() - 1
        signals.SignalPublisher.instance()._signal_builder_wrappers["key"] = signal_builder_wrapper

        async def auto_remove_wrapper(key):
            await asyncio.sleep(0.1)
            signals.SignalPublisher.instance()._signal_builder_wrappers.pop(key)
        asyncio.create_task(auto_remove_wrapper("key"))
        await asyncio_tools.wait_asyncio_next_cycle()
        await signals.SignalPublisher.instance()._schedule_signal_auto_emit("key", 0.001)
        assert _emit_signal_if_necessary_mock.call_count > 1


def test_register_timeout_if_any(publisher, signal_builder_wrapper):
    with mock.patch.object(asyncio, "create_task", mock.Mock(return_value="created_task")) as create_task_mock, \
            mock.patch.object(signals.SignalPublisher.instance(), "_schedule_signal_auto_emit",
                              mock.Mock(return_value="task")) as _schedule_signal_auto_emit_mock:
        with pytest.raises(KeyError):
            signals.SignalPublisher.instance()._register_timeout_if_any("key")
        create_task_mock.assert_not_called()
        _schedule_signal_auto_emit_mock.assert_not_called()

        assert not signals.SignalPublisher.instance()._timeout_watcher_tasks
        signal_builder_wrapper.timeout = signal_builder_wrapper.NO_TIMEOUT_VALUE
        signals.SignalPublisher.instance()._signal_builder_wrappers["key"] = signal_builder_wrapper
        signals.SignalPublisher.instance()._register_timeout_if_any("key")
        create_task_mock.assert_not_called()
        _schedule_signal_auto_emit_mock.assert_not_called()
        assert not signals.SignalPublisher.instance()._timeout_watcher_tasks

        signal_builder_wrapper.timeout = 1
        signals.SignalPublisher.instance()._register_timeout_if_any("key")
        create_task_mock.assert_called_once_with("task")
        _schedule_signal_auto_emit_mock.assert_called_once_with("key", 1)
        assert signals.SignalPublisher.instance()._timeout_watcher_tasks["key"] == "created_task"


def test_unregister_timeout(publisher):
    task = mock.Mock(cancel=mock.Mock())
    signals.SignalPublisher.instance()._unregister_timeout("key")
    task.cancel.assert_not_called()
    signals.SignalPublisher.instance()._timeout_watcher_tasks["key"] = task
    signals.SignalPublisher.instance()._unregister_timeout("key")
    task.cancel.assert_called_once()
