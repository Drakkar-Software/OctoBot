#  Drakkar-Software OctoBot-Trading
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

import octobot_trading.constants as constants
import octobot_trading.personal_data.portfolios.asset as asset_class


class SpotAsset(asset_class.Asset):
    def __eq__(self, other):
        if isinstance(other, SpotAsset):
            return self.available == other.available and self.total == other.total
        return False

    def update(self, available=constants.ZERO, total=constants.ZERO):
        """
        Update asset portfolio
        :param available: the available delta
        :param total: the total delta
        :return: True if updated
        """
        if available == constants.ZERO and total == constants.ZERO:
            return False

        with self.update_or_restore():
            self.available += self._ensure_update_validity(self.available, available)
            self.total += self._ensure_update_validity(self.total, total)
            return True

    def set(self, available, total):
        """
        Set available and total values for portfolio asset
        :param available: the available value
        :param total: the total value
        :return: True if updated
        """
        if available == self.available and total == self.total:
            return False
        self.available = available
        self.total = total
        return True

    def reset(self):
        """
        Reset asset portfolio to zero
        """
        self.set(available=constants.ZERO, total=constants.ZERO)
