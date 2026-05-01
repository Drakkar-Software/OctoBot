#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
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

from octobot.community.wallet_backend import community_wallet
from octobot.community.wallet_backend.community_wallet import (
    WalletBackend,
    WalletInfo,
)
from octobot.community.wallet_backend import errors
from octobot.community.wallet_backend.errors import (
    WalletError,
    WalletAlreadyExistsError,
    AdminWalletAlreadyExistsError,
    WalletNotFoundError,
    InvalidPassphraseError,
    CannotRemoveLastWalletError,
    CannotRemoveAdminWalletError,
    InvalidPrivateKeyError,
    PassphraseTooShortError,
)
from octobot.community.wallet_backend import wallet_storage
from octobot.community.wallet_backend.wallet_storage import (
    WalletStorage,
    ConfigJsonWalletStorage,
    DedicatedFileWalletStorage,
    EnvVarWalletStorage,
    build_wallet_storage,
)

__all__ = [
    "WalletBackend",
    "WalletInfo",
    "WalletError",
    "WalletAlreadyExistsError",
    "AdminWalletAlreadyExistsError",
    "WalletNotFoundError",
    "InvalidPassphraseError",
    "CannotRemoveLastWalletError",
    "CannotRemoveAdminWalletError",
    "InvalidPrivateKeyError",
    "PassphraseTooShortError",
    "WalletStorage",
    "ConfigJsonWalletStorage",
    "DedicatedFileWalletStorage",
    "EnvVarWalletStorage",
    "build_wallet_storage",
]
