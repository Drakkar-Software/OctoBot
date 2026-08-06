#  Drakkar-Software OctoBot-Tentacles-Manager
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
import octobot_commons.logging as logging
import octobot_commons.multiprocessing_util as multiprocessing_util
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.loaders as loaders
import octobot_tentacles_manager.util as util
import octobot_tentacles_manager.util.tentacles_filesystem_lock as tentacles_filesystem_lock


async def manage_tentacles(worker, tentacle_names, tentacles_path_or_url=None, aiohttp_session=None,
                           authenticator=None) -> int:
    logger = logging.get_logger(__name__)
    lock_file_path = tentacles_filesystem_lock.get_tentacles_install_lock_file_path()
    try:
        async with multiprocessing_util.async_filesystem_based_lock(lock_file_path):
            return await _manage_tentacles_unlocked(
                worker, tentacle_names, tentacles_path_or_url, aiohttp_session, authenticator
            )
    except multiprocessing_util.FilesystemBasedLockTimeoutError:
        logger.error("Could not acquire tentacles install lock")
        return 1


async def _manage_tentacles_unlocked(worker, tentacle_names, tentacles_path_or_url=None, aiohttp_session=None,
                                     authenticator=None) -> int:
    errors_count = 0
    logger = logging.get_logger(__name__)
    try:
        if tentacles_path_or_url is not None:
            session = authenticator.get_aiohttp_session() if authenticator and authenticator.is_logged_in() \
                else aiohttp_session
            await util.fetch_and_extract_tentacles(constants.TENTACLES_INSTALL_TEMP_DIR,
                                                   tentacles_path_or_url,
                                                   session)
        errors_count = await worker.process(tentacle_names)
    except Exception as e:
        logger.exception(e, True, f"Exception during {worker.__class__.__name__} processing: {e}")
        # ensure error is taken into account
        if errors_count == 0:
            errors_count = 1
    finally:
        if tentacles_path_or_url is not None:
            util.cleanup_temp_dirs(constants.TENTACLES_INSTALL_TEMP_DIR)
        try:
            # reload tentacles data
            loaders.reload_tentacle_by_tentacle_class()
        except Exception as e:
            logger.exception(e, True, f"Exception while reloading tentacles data: {e}")
            errors_count = 1
    return errors_count
