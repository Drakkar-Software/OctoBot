#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
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

import enum


class MobileUiState(enum.StrEnum):
    NOT_CONFIGURED = "not_configured"
    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    READY = "ready"
    ERROR = "error"


class MobileUiErrorCode(enum.StrEnum):
    NOT_CONFIGURED = "not_configured"
    MANIFEST_FETCH_FAILED = "manifest_fetch_failed"
    MANIFEST_INVALID = "manifest_invalid"
    SIGNATURE_INVALID = "signature_invalid"
    DOWNLOAD_FAILED = "download_failed"
    INTEGRITY_CHECK_FAILED = "integrity_check_failed"
    INSTALL_FAILED = "install_failed"
    ROLLBACK_REJECTED = "rollback_rejected"
