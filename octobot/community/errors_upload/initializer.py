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
import time

import octobot.community.errors_upload.errors_uploader as errors_uploader
import octobot.community.errors_upload.error_model as error_model
import octobot_commons.logging as logging
import octobot.constants as constants


class _UploadWrapper:
    def __init__(self, upload_url, config):
        self._config = config
        self._metrics_id = self._get_metrics_id()
        self._uploader = errors_uploader.ErrorsUploader(
            upload_url
        )

    def upload_if_necessary(self, exception, error_message):
        if constants.UPLOAD_ERRORS and (constants.IS_CLOUD_ENV or self._config.get_metrics_enabled()):
            self._uploader.schedule_error_upload(
                error_model.Error(
                    exception, error_message, time.time(), self._metrics_id
                )
            )

    def _get_metrics_id(self):
        try:
            return self._config.get_metrics_id()
        except KeyError:
            return constants.DEFAULT_METRICS_ID


def register_error_uploader(upload_url, config):
    upload_wrapper = _UploadWrapper(upload_url, config)
    logging.BotLogger.register_error_callback(upload_wrapper.upload_if_necessary)
