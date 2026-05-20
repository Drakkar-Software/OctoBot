#  This file is part of OctoBot Sync (https://github.com/Drakkar-Software/OctoBot)
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


class OctobotSyncError(Exception):
    """
    Parent class for all octobot sync errors
    """


class OctobotSyncIdentityMissingError(OctobotSyncError):
    """
    Raised when an identity is missing from the context
    """
    pass


class OctobotSyncCollectionMissingError(OctobotSyncError):
    """
    Raised when a collection is missing from the context
    """
    pass


class OctobotSyncCryptoFormatError(OctobotSyncError):
    """Raised when an encrypted blob or wire payload is malformed."""

    pass


class OctobotSyncCryptoDecryptError(OctobotSyncError):
    """Raised when ciphertext cannot be decrypted (wrong key, tampering, etc.)."""

    pass


class OctobotSyncWalletNotFoundError(OctobotSyncError):
    """Raised when no wallet exists for the requested address."""

    pass


class OctobotSyncAccountIdMissingError(OctobotSyncError):
    """Raised when account_id is missing from the store context."""

    pass
