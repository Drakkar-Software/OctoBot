#  Drakkar-Software OctoBot-Interfaces
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


# utility URLs
# top 250 sorted currencies (expects a page id at the end)
CURRENCIES_LIST_URL = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page="
ALL_SYMBOLS_URL = "https://api.coingecko.com/api/v3/coins/list"

# config keys
CONFIG_WATCHED_SYMBOLS = "watched_symbols"

# web interface keys
GLOBAL_CONFIG_KEY = "global_config"
EVALUATOR_CONFIG_KEY = "evaluator_config"
TENTACLES_CONFIG_KEY = "tentacle_config"
DEACTIVATE_OTHERS = "deactivate_others"
TRADING_CONFIG_KEY = "trading_config"
UPDATED_CONFIG_SEPARATOR = "_"
ACTIVATION_KEY = "activation"
TENTACLE_CLASS_NAME = "name"
STARTUP_CONFIG_KEY = "startup_config"

# backtesting
BOT_TOOLS_BACKTESTING = "backtesting"
BOT_TOOLS_BACKTESTING_SOURCE = "backtesting_source"
BOT_PREPARING_BACKTESTING = "preparing_backtesting"

# strategy optimizer
BOT_TOOLS_STRATEGY_OPTIMIZER = "strategy_optimizer"

# data collector
BOT_TOOLS_DATA_COLLECTOR = "data_collector"
BOT_TOOLS_SOCIAL_DATA_COLLECTOR = "social_data_collector"

PRODUCT_HUNT_ANNOUNCEMENT = "product_hunt_announcement"
PRODUCT_HUNT_ANNOUNCEMENT_DAY = 1720594860  # Wednesday, July 10, 2024 7:01:00 AM UTC
