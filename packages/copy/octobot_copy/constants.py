#  Drakkar-Software OctoBot
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
import decimal

import octobot_commons.constants


# Rebalance planner thresholds
ALLOWED_1_TO_1_SWAP_COUNTS = 1
MIN_RATIO_TO_SELL = decimal.Decimal("0.0001")  # 1/10000
QUOTE_ASSET_TO_TARGETED_SWAP_RATIO_THRESHOLD = decimal.Decimal("0.1")  # 10%

# Index / rebalancing trading config keys (shared by planner, index trading mode, profiles).
CONFIG_INDEX_CONTENT = "index_content"
CONFIG_REBALANCE_TRIGGER_MIN_PERCENT = "rebalance_trigger_min_percent"
CONFIG_REBALANCE_TRIGGER_PROFILES = "rebalance_trigger_profiles"
CONFIG_SELECTED_REBALANCE_TRIGGER_PROFILE = "selected_rebalance_trigger_profile"
CONFIG_REBALANCE_TRIGGER_PROFILE_NAME = "name"
CONFIG_REBALANCE_TRIGGER_PROFILE_MIN_PERCENT = "min_percent"

# Exchange / order lifecycle (seconds)
FILL_ORDER_TIMEOUT = 60
FILL_ORDER_WAIT_TIME = 5

# Mirrored orphan grace: max |simulated_copier_pair_share − ref_pair_share| to allow deferral
DEFAULT_MIRRORED_ORPHAN_GRACE_PAIR_RATIO_MAX_DELTA = decimal.Decimal("0.02") # 2%
DEFAULT_MIRRORED_ORPHAN_ORDERS_GRACE_ABORT_THRESHOLD = 2
DEFAULT_MISSED_SIGNALS_GRACE_ABORT_THRESHOLD = 10

# Account keys
PORTFOLIO_ASSET_ALLOCATION_RATIO = "allocation_ratio"

# Account copy settings
DEFAULT_COPY_WAITING_TIME = octobot_commons.constants.HOURS_TO_SECONDS * 4 # wake up every 4 hours by default

# Order tags: reference mirror orders vs rebalance limit orders (orphan cancellation scope)
MIRRORED_ORDER_TAG = "mirrored_order"
REBALANCER_ORDER_TAG = "rebalancer_order"
