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
import asyncio
import aiohttp

import octobot_commons.logging


class ErrorsUploader:
    """
    ErrorsUploader manages errors posts to the error url
    """

    def __init__(self, upload_url):
        self.upload_url = upload_url
        self.loop = None
        self.upload_delay = 5

        self._to_upload_errors = []
        self._upload_task = None

        self.logger = octobot_commons.logging.get_logger(self.__class__.__name__)

    def schedule_error_upload(self, error):
        """
        Called to schedule an error upload
        :param error: the octobot_commons.logging.error_model.Error to upload
        """
        self._add_error(error)
        self._ensure_upload_task()

    def _add_error(self, error):
        for existing_error in self._to_upload_errors:
            # first check if error is equivalent to an existing one
            if existing_error.is_equivalent(error):
                existing_error.merge_equivalent(error)
                return
        self._to_upload_errors.append(error)

    def _ensure_upload_task(self):
        try:
            if self._ensure_event_loop() and (self._upload_task is None or self._upload_task.done()):
                self._schedule_upload()
        except Exception as err:
            self.logger.exception(
                err,
                True,
                f"Error when uploading exception: {err}",
                skip_post_callback=True,
            )

    async def _upload_errors(self, session, errors):
        async with session.post(self.upload_url, json=self._get_formatted_errors(errors)) as resp:
            if resp.status != 200:
                self.logger.error(
                    f"Impossible to upload error : status code: {resp.status}, text: {await resp.text()}",
                    skip_post_callback=True
                )

    @staticmethod
    def _get_formatted_errors(errors):
        return [error.to_dict() for error in errors]

    def _schedule_upload(self):
        self._upload_task = self.loop.create_task(
            self._upload_soon()
        )

    async def _upload_soon(self):
        try:
            await asyncio.sleep(self.upload_delay)

            if self._to_upload_errors:
                async with aiohttp.ClientSession() as session:
                    errors = self._to_upload_errors
                    self._to_upload_errors = []
                    await self._upload_errors(session, errors)
                    self.logger.debug(f"Uploaded {len(errors)} errors")
        except Exception as err:
            self.logger.exception(
                err, True, f"Error when uploading exception: {err}", skip_post_callback=True
            )
        finally:
            if self._to_upload_errors:
                # reschedule if new errors arrived during upload
                self._schedule_upload()

    def _ensure_event_loop(self):
        if self.loop is not None:
            if self.loop.is_running():
                return True
            # otherwise, use the current loop
        try:
            self.loop = asyncio.get_event_loop()
            return True
        except RuntimeError:
            return False
