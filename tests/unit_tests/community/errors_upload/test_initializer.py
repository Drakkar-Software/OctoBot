#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
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

import octobot.constants as constants
import octobot.community as community
import octobot.community.errors_upload.initializer as initializer
import octobot_commons.logging as logging
import octobot_commons.logging.logging_util as logging_util
from tests.unit_tests.community.errors_upload import UPLOADER_URL


@pytest.fixture()
def upload_wrapper():
    config = mock.Mock()
    config.get_metrics_id = mock.Mock(return_value="abc")
    return initializer._UploadWrapper(UPLOADER_URL, config)


def test_register_error_uploader():
    config = mock.Mock()
    upload_wrapper = mock.Mock()
    upload_wrapper.upload_if_necessary = "upload_if_necessary"
    previous_callback = logging_util._ERROR_CALLBACK
    with mock.patch.object(initializer, "_UploadWrapper", mock.Mock(return_value=upload_wrapper)) \
            as _UploadWrapper_mock:
        community.register_error_uploader(UPLOADER_URL, config)
        _UploadWrapper_mock.assert_called_once_with(UPLOADER_URL, config)
        assert logging_util._ERROR_CALLBACK == "upload_if_necessary"
    # restore callback
    logging.BotLogger.register_error_callback(previous_callback)


def test_UploadWrapper_upload_if_necessary(upload_wrapper):
    with mock.patch.object(constants, "UPLOAD_ERRORS", True):
        with mock.patch.object(upload_wrapper._uploader, "schedule_error_upload", mock.Mock()) \
                as schedule_error_upload_mock:
            with mock.patch.object(upload_wrapper._config, "get_metrics_enabled", mock.Mock(return_value=False)) \
                 as get_metrics_enabled_mock:
                upload_wrapper.upload_if_necessary(None, "message")
                get_metrics_enabled_mock.assert_called_once()
                schedule_error_upload_mock.assert_not_called()
            with mock.patch.object(upload_wrapper._config, "get_metrics_enabled", mock.Mock(return_value=True)) \
                 as get_metrics_enabled_mock:
                upload_wrapper.upload_if_necessary(None, "message")
                get_metrics_enabled_mock.assert_called_once()
                schedule_error_upload_mock.assert_called_once()
    with mock.patch.object(constants, "UPLOAD_ERRORS", False):
        with mock.patch.object(upload_wrapper._uploader, "schedule_error_upload", mock.Mock()) \
                as schedule_error_upload_mock:
            with mock.patch.object(upload_wrapper._config, "get_metrics_enabled", mock.Mock(return_value=True)) \
                 as get_metrics_enabled_mock:
                upload_wrapper.upload_if_necessary(None, "message")
                get_metrics_enabled_mock.assert_not_called()
                schedule_error_upload_mock.assert_not_called()


def test_get_metrics_id(upload_wrapper):
    def raiser():
        return {}["plop"]
    assert upload_wrapper._get_metrics_id() == "abc"
    with mock.patch.object(upload_wrapper._config, "get_metrics_id", raiser):
        assert upload_wrapper._get_metrics_id() == constants.DEFAULT_METRICS_ID
