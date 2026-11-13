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
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.constants as constants
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.enums as enums
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.errors as errors
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.manifest as manifest
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.store as store
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.serving as serving
except ImportError:
    from . import constants  # type: ignore[no-redef]
    from . import enums  # type: ignore[no-redef]
    from . import errors  # type: ignore[no-redef]
    from . import manifest  # type: ignore[no-redef]
    from . import store  # type: ignore[no-redef]
    from . import serving  # type: ignore[no-redef]

MobileUiError = errors.MobileUiError
MobileUiNotConfiguredError = errors.MobileUiNotConfiguredError
ManifestFetchError = errors.ManifestFetchError
ManifestInvalidError = errors.ManifestInvalidError
SignatureError = errors.SignatureError
FileDownloadError = errors.FileDownloadError
FileIntegrityError = errors.FileIntegrityError
MobileUiInstallError = errors.MobileUiInstallError
ManifestRollbackError = errors.ManifestRollbackError

MobileUiState = enums.MobileUiState
MobileUiErrorCode = enums.MobileUiErrorCode

Manifest = manifest.Manifest
ManifestFile = manifest.ManifestFile
parse_and_validate = manifest.parse_and_validate
signed_payload = manifest.signed_payload
verify_signature = manifest.verify_signature
parse_public_keys = manifest.parse_public_keys
verify_signature_any = manifest.verify_signature_any
validate_relative_path = manifest.validate_relative_path

MobileUiStore = store.MobileUiStore
MobileUiStatus = store.MobileUiStatus
build_default_store = store.build_default_store

add_mobile_ui_routes = serving.add_mobile_ui_routes
