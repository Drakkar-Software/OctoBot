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

try:
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.enums as enums
except ImportError:
    try:
        import mobile_ui.enums as enums  # type: ignore[no-redef]
    except ImportError:
        import enums  # type: ignore[no-redef]


class MobileUiError(Exception):
    code: enums.MobileUiErrorCode = enums.MobileUiErrorCode.INSTALL_FAILED

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class MobileUiNotConfiguredError(MobileUiError):
    code = enums.MobileUiErrorCode.NOT_CONFIGURED


class ManifestFetchError(MobileUiError):
    code = enums.MobileUiErrorCode.MANIFEST_FETCH_FAILED


class ManifestInvalidError(MobileUiError):
    code = enums.MobileUiErrorCode.MANIFEST_INVALID


class SignatureError(MobileUiError):
    code = enums.MobileUiErrorCode.SIGNATURE_INVALID


class FileDownloadError(MobileUiError):
    code = enums.MobileUiErrorCode.DOWNLOAD_FAILED


class FileIntegrityError(MobileUiError):
    code = enums.MobileUiErrorCode.INTEGRITY_CHECK_FAILED


class MobileUiInstallError(MobileUiError):
    code = enums.MobileUiErrorCode.INSTALL_FAILED


class ManifestRollbackError(MobileUiError):
    code = enums.MobileUiErrorCode.ROLLBACK_REJECTED

