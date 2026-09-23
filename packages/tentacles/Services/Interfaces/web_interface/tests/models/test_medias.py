#  Drakkar-Software OctoBot-Tentacles
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

import os

import pytest

import octobot_commons.constants as commons_constants
import octobot_commons.user_root_folder_provider as user_root_folder_provider
import tentacles.Services.Interfaces.web_interface.models.medias as medias_model


class TestIsValidProfileImagePath:
    @pytest.fixture(autouse=True)
    def setup_provider(self, tmp_path, monkeypatch):
        self.child_user_root = tmp_path / "child_user"
        self.master_user_root = tmp_path / "master_user"
        self.child_user_root.mkdir()
        self.master_user_root.mkdir()
        provider = user_root_folder_provider.UserRootFolderProvider.instance()
        provider.set_root(str(self.child_user_root))
        monkeypatch.setenv(
            commons_constants.ENV_OCTOBOT_SYNC_DATA_ROOT,
            str(self.master_user_root),
        )
        yield
        provider.set_root(None)
        monkeypatch.delenv(commons_constants.ENV_OCTOBOT_SYNC_DATA_ROOT, raising=False)

    def test_accepts_child_local_profile_image(self):
        profiles_root = self.child_user_root / commons_constants.PROFILES_FOLDER
        profile_path = profiles_root / "daily_trading" / "default_profile.png"
        profile_path.parent.mkdir(parents=True)
        profile_path.touch()
        assert medias_model.is_valid_profile_image_path(str(profile_path))

    def test_accepts_master_sync_data_profile_image(self):
        profiles_root = self.master_user_root / commons_constants.PROFILES_FOLDER
        profile_path = profiles_root / "daily_trading" / "default_profile.png"
        profile_path.parent.mkdir(parents=True)
        profile_path.touch()
        assert medias_model.is_valid_profile_image_path(str(profile_path))

    def test_rejects_path_outside_allowed_roots(self):
        outside_path = self.child_user_root / "outside.png"
        outside_path.touch()
        assert medias_model.is_valid_profile_image_path(str(outside_path)) is False

    def test_rejects_path_traversal(self):
        profiles_root = self.child_user_root / commons_constants.PROFILES_FOLDER
        profiles_root.mkdir(parents=True)
        traversal_path = os.path.join(str(profiles_root), "..", "secret.png")
        assert medias_model.is_valid_profile_image_path(traversal_path) is False
