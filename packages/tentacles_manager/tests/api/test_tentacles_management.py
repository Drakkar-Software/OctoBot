#  Drakkar-Software OctoBot-Tentacles-Manager
#  Copyright (c) Drakkar-Software, All rights reserved.

import contextlib
import os

import mock
import pytest

import octobot_commons.multiprocessing_util as multiprocessing_util
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.api.util.tentacles_management as tentacles_management


pytestmark = pytest.mark.asyncio


class TestManageTentaclesFilesystemLock:
    @pytest.mark.asyncio
    async def test_manage_tentacles_acquires_filesystem_lock(self):
        worker = mock.Mock()
        worker.process = mock.AsyncMock(return_value=0)
        worker.__class__.__name__ = "InstallWorker"
        captured_lock_paths = []

        @contextlib.asynccontextmanager
        async def mock_lock(lock_file_path):
            captured_lock_paths.append(lock_file_path)
            yield

        with mock.patch(
            "octobot_commons.user_root_folder_provider.get_user_reference_tentacle_config_path",
            return_value="/master/reference",
        ), mock.patch.object(
            multiprocessing_util,
            "async_filesystem_based_lock",
            mock_lock,
        ), mock.patch.object(
            tentacles_management.loaders,
            "reload_tentacle_by_tentacle_class",
            mock.Mock(),
        ):
            result = await tentacles_management.manage_tentacles(worker, None)

        assert result == 0
        assert captured_lock_paths == [
            os.path.join("/master/reference", constants.TENTACLES_INSTALL_LOCK_FILE_NAME)
        ]
        worker.process.assert_awaited_once_with(None)

    @pytest.mark.asyncio
    async def test_manage_tentacles_lock_timeout_returns_error(self):
        worker = mock.Mock()
        worker.process = mock.AsyncMock(return_value=0)
        worker.__class__.__name__ = "InstallWorker"

        @contextlib.asynccontextmanager
        async def mock_lock(_lock_file_path):
            raise multiprocessing_util.FilesystemBasedLockTimeoutError("timeout")
            yield  # pragma: no cover

        with mock.patch.object(
            multiprocessing_util,
            "async_filesystem_based_lock",
            mock_lock,
        ):
            result = await tentacles_management.manage_tentacles(worker, None)

        assert result == 1
        worker.process.assert_not_awaited()
