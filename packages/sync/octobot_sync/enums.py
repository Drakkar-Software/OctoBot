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

import enum


class Collections(enum.StrEnum):
    USER_DATA = "user-data"
    USER_ACCOUNTS = "user-accounts"
    USER_ACCOUNTS_AUTH = "user-accounts-auth"
    USER_ACCOUNTS_TRADING = "user-accounts-trading"
    USER_ACCOUNTS_HISTORY = "user-accounts-history"
    USER_SETTINGS = "user-settings"
    USER_ACTIONS = "user-actions"
    DEBUG = "debug"

class TemporaryCollections(enum.StrEnum):
    # --- TEMPORARY: append-only product signals collection ---------------------
    # Scaffolding to store signals as an append-only (by_timestamp) log, keyed by
    # PRODUCT (not user identity): every push appends the payload as a {ts, data}
    # element rather than overwriting, and pulls fetch only newer elements via
    # ?checkpoint=. The path is product-scoped, so it carries no {identity} segment
    # and cannot use the "self" role; access is granted to the node's self-signed
    # root device cap (ROLE_ROOT_DEVICE). This whole block (the constant and the
    # CollectionConfig entry below) is temporary and will be REMOVED once the signals
    # storage design is finalized.
    TEMP_PRODUCT_SIGNALS = "product-signals"
    # Temporary user-strategies collection; remove when strategies storage is finalized.
    TEMP_USER_STRATEGIES = "user-strategies"