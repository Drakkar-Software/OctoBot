#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
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
import mock
import contextlib
import asyncio
import aiohttp

import octobot.community as community
from tests.unit_tests.community.errors_upload import error_uploader, basic_error, exception_error


def test_schedule_error_upload(error_uploader, basic_error):
    with mock.patch.object(error_uploader, "_add_error", mock.Mock()) as _add_error_mock, \
         mock.patch.object(error_uploader, "_ensure_upload_task", mock.Mock()) as _ensure_upload_task_mock:
        error_uploader.schedule_error_upload(basic_error)
        _add_error_mock.assert_called_once_with(basic_error)
        _ensure_upload_task_mock.assert_called_once()


def test_add_error(error_uploader, basic_error):
    with mock.patch.object(basic_error, "merge_equivalent", mock.Mock()) as merge_equivalent_mock:
        with mock.patch.object(basic_error, "is_equivalent", mock.Mock(return_value=False)) as is_equivalent_mock:
            error_uploader._add_error(basic_error)
            merge_equivalent_mock.assert_not_called()
            is_equivalent_mock.assert_not_called()
            assert error_uploader._to_upload_errors == [basic_error]

            error_uploader._add_error(basic_error)
            merge_equivalent_mock.assert_not_called()
            is_equivalent_mock.assert_called_once_with(basic_error)
            assert error_uploader._to_upload_errors == [basic_error, basic_error]

        with mock.patch.object(basic_error, "is_equivalent", mock.Mock(return_value=True)) as is_equivalent_mock:
            error_uploader._add_error(basic_error)
            merge_equivalent_mock.assert_called_once_with(basic_error)
            is_equivalent_mock.assert_called_once_with(basic_error)
            assert error_uploader._to_upload_errors == [basic_error, basic_error]


def test_ensure_upload_task(error_uploader):
    error_uploader.logger = mock.Mock()
    with mock.patch.object(error_uploader.logger, "exception", mock.Mock()) as exception_mock:
        with mock.patch.object(error_uploader, "_schedule_upload", mock.Mock()) as _schedule_upload_mock:
            with mock.patch.object(error_uploader, "_ensure_event_loop", mock.Mock(return_value=False)) \
                    as _ensure_event_loop_mock:
                error_uploader._ensure_upload_task()
                _ensure_event_loop_mock.assert_called_once()
                _schedule_upload_mock.assert_not_called()
                exception_mock.assert_not_called()
            with mock.patch.object(error_uploader, "_ensure_event_loop", mock.Mock(return_value=True)) \
                    as _ensure_event_loop_mock:
                error_uploader._ensure_upload_task()
                _ensure_event_loop_mock.assert_called_once()
                _schedule_upload_mock.assert_called_once()
                exception_mock.assert_not_called()
                _ensure_event_loop_mock.reset_mock()
                _schedule_upload_mock.reset_mock()

                error_uploader._upload_task = mock.Mock()
                with mock.patch.object(error_uploader._upload_task, "done", mock.Mock(return_value=False)) \
                        as _upload_task_mock:
                    error_uploader._ensure_upload_task()
                    _ensure_event_loop_mock.assert_called_once()
                    _upload_task_mock.assert_called_once()
                    _schedule_upload_mock.assert_not_called()
                    exception_mock.assert_not_called()
                    _ensure_event_loop_mock.reset_mock()
                with mock.patch.object(error_uploader._upload_task, "done", mock.Mock(return_value=True)) \
                        as _upload_task_mock:
                    error_uploader._ensure_upload_task()
                    _ensure_event_loop_mock.assert_called_once()
                    _upload_task_mock.assert_called_once()
                    _schedule_upload_mock.assert_called_once()
                    exception_mock.assert_not_called()
                    _ensure_event_loop_mock.reset_mock()
                with mock.patch.object(error_uploader._upload_task, "done", mock.Mock(side_effect=RuntimeError())) \
                        as _upload_task_mock:
                    error_uploader._ensure_upload_task()
                    _ensure_event_loop_mock.assert_called_once()
                    _upload_task_mock.assert_called_once()
                    _schedule_upload_mock.assert_called_once()
                    exception_mock.assert_called_once()


@pytest.mark.asyncio
async def test_upload_errors(error_uploader, basic_error, exception_error):
    session = mock.Mock()
    resp = mock.Mock()
    resp.status = 400
    resp.text = mock.AsyncMock(return_value="text")
    post_mock = mock.AsyncMock(return_value=resp)

    @contextlib.asynccontextmanager
    async def post(*args, **kwargs):
        yield await post_mock(*args, **kwargs)
    session.post = post
    errors = [basic_error, exception_error]
    error_uploader.logger = mock.Mock()
    with mock.patch.object(error_uploader.logger, "error", mock.Mock(return_value=None)) as error_mock, \
         mock.patch.object(error_uploader, "_get_formatted_errors", mock.Mock(return_value=None)) \
         as _get_formatted_errors_mock:
        await error_uploader._upload_errors(session, errors)
        post_mock.assert_called_once_with(error_uploader.upload_url, json=None)
        error_mock.assert_called_once()
        post_mock.reset_mock()
        error_mock.reset_mock()

        resp.status = 200
        await error_uploader._upload_errors(session, errors)
        post_mock.assert_called_once_with(error_uploader.upload_url, json=None)
        error_mock.assert_not_called()


def test_get_formatted_errors(error_uploader, basic_error, exception_error):
    with mock.patch.object(community.Error, "to_dict", mock.Mock(return_value={})) as to_dict_mock:
        assert error_uploader._get_formatted_errors([basic_error, exception_error]) == [{}, {}]
        assert to_dict_mock.call_count == 2


def test_schedule_upload(error_uploader):
    error_uploader.loop = mock.Mock()
    error_uploader.loop.create_task = mock.Mock(return_value="return")
    with mock.patch.object(error_uploader, "_upload_soon", mock.Mock(return_value="return")) as _upload_soon_mock:
        error_uploader._schedule_upload()
        _upload_soon_mock.assert_called_once()
        error_uploader.loop.create_task.assert_called_once_with("return")
        assert error_uploader._upload_task == "return"


@pytest.mark.asyncio
async def test_upload_soon(error_uploader, basic_error):
    _session_mock = mock.AsyncMock(return_value="plop")

    @contextlib.asynccontextmanager
    async def session_mock(*args, **kwargs):
        yield await _session_mock(*args, **kwargs)
    with mock.patch.object(asyncio, "sleep", mock.AsyncMock()) as sleep_mock, \
         mock.patch.object(aiohttp, "ClientSession", session_mock), \
         mock.patch.object(error_uploader, "_schedule_upload", mock.Mock()) as _schedule_upload_mock:
        with mock.patch.object(error_uploader, "_upload_errors", mock.AsyncMock()) as _upload_errors_mock:

            # no error to upload
            await error_uploader._upload_soon()
            sleep_mock.assert_called_once_with(error_uploader.upload_delay)
            _session_mock.assert_not_called()
            _upload_errors_mock.assert_not_called()
            _schedule_upload_mock.assert_not_called()
            sleep_mock.reset_mock()

            # errors to upload
            error_uploader._to_upload_errors = [basic_error]
            await error_uploader._upload_soon()
            assert error_uploader._to_upload_errors == []
            sleep_mock.assert_called_once_with(error_uploader.upload_delay)
            _session_mock.assert_called_once()
            _upload_errors_mock.assert_called_once_with("plop", [basic_error])
            _schedule_upload_mock.assert_not_called()
            sleep_mock.reset_mock()
            _session_mock.reset_mock()
            _upload_errors_mock.reset_mock()

        async def upload_errors_adding_errors(*_):
            error_uploader._to_upload_errors = [basic_error]
        with mock.patch.object(error_uploader, "_upload_errors", upload_errors_adding_errors):
            # errors to upload
            error_uploader._to_upload_errors = [basic_error]
            await error_uploader._upload_soon()
            sleep_mock.assert_called_once_with(error_uploader.upload_delay)
            _session_mock.assert_called_once()
            # reschedule call
            _schedule_upload_mock.assert_called_once()
            sleep_mock.reset_mock()
            _session_mock.reset_mock()


def test_ensure_event_loop(error_uploader):
    error_uploader.loop = mock.Mock()
    with mock.patch.object(asyncio, "get_event_loop", mock.Mock(return_value="loop")) as get_event_loop_mock:
        with mock.patch.object(error_uploader.loop, "is_running", mock.Mock(return_value=True)) as is_running_mock:
            error_uploader._ensure_event_loop()
            is_running_mock.assert_called_once()
            get_event_loop_mock.assert_not_called()
        with mock.patch.object(error_uploader.loop, "is_running", mock.Mock(return_value=False)) as is_running_mock:
            assert error_uploader._ensure_event_loop()
            is_running_mock.assert_called_once()
            get_event_loop_mock.assert_called_once()
            assert error_uploader.loop == "loop"
    error_uploader.loop = None
    with mock.patch.object(asyncio, "get_event_loop", mock.Mock(side_effect=RuntimeError())) as get_event_loop_mock:
        assert error_uploader._ensure_event_loop() is False
        get_event_loop_mock.assert_called_once()
