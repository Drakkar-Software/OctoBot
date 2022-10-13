#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
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
import os

import octobot_trading.exchanges as exchanges


def get_test_exchange_manager(config, exchange_name):
    exchange_manager = exchanges.ExchangeManager(config, exchange_name)
    # customize exchange id to include test name (useful in possible memory issues)
    exchange_manager.id = f"{exchange_manager.id}[{os.environ.get('PYTEST_CURRENT_TEST')}]"
    return exchange_manager
