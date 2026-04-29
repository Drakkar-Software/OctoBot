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
import decimal

import octobot_trading.constants as constants
import octobot_trading.personal_data.portfolios.asset as asset_class


class MarginAsset(asset_class.Asset):
    def __init__(self, name, available, total,
                 borrowed=constants.ZERO,
                 interest=constants.ZERO,
                 locked=constants.ZERO):
        super().__init__(name, available, total)
        self.borrowed: decimal.Decimal = borrowed
        self.interest: decimal.Decimal = interest
        self.locked: decimal.Decimal = locked

    def __str__(self):
        return super().__str__() + " | " \
                                   f"Borrowed: {float(self.borrowed)} | " \
                                   f"Interest: {float(self.interest)} | " \
                                   f"Locked: {float(self.locked)}"

    def __eq__(self, other):
        if isinstance(other, MarginAsset):
            return self.available == other.available and self.total == other.total and \
                   self.borrowed == other.borrowed and self.interest == other.interest and self.locked == other.locked
        return False

    def _specific_restore_unavailable_from_other(self, other_asset):
        if other_asset.borrowed != constants.ZERO:
            self.borrowed = self.borrowed + other_asset.borrowed
        if other_asset.interest != constants.ZERO:
            self.interest = self.interest + other_asset.interest
        if other_asset.locked != constants.ZERO:
            self.locked = self.locked + other_asset.locked

    def update(self, available=constants.ZERO, total=constants.ZERO, borrowed=constants.ZERO,
               interest=constants.ZERO, locked=constants.ZERO):
        """
        Update asset portfolio
        :param available: the available delta
        :param total: the total delta
        :param borrowed: the borrowed delta
        :param interest: the interest delta
        :param locked: the locked delta
        :return: True if updated
        """
        if available == constants.ZERO and total == constants.ZERO and borrowed == constants.ZERO and \
                interest == constants.ZERO and locked == constants.ZERO:
            return False
        self.available += self._ensure_update_validity(self.available, available)
        self.total += self._ensure_update_validity(self.total, total)
        self.borrowed += self._ensure_update_validity(self.borrowed, borrowed)
        self.interest += self._ensure_update_validity(self.interest, interest)
        self.locked += self._ensure_update_validity(self.locked, locked)
        return True

    def set(self, available=constants.ZERO, total=constants.ZERO, borrowed=constants.ZERO,
            interest=constants.ZERO, locked=constants.ZERO):
        """
        Set available, total, initial_margin, margin_balance, position_initial_margin and maintenance_margin
        values for portfolio asset
        :param available: the available value
        :param total: the total value
        :param borrowed: the borrowed value
        :param interest: the interest value
        :param locked: the locked value
        :return: True if updated
        """
        if available == self.available and total == self.total and borrowed == self.borrowed and \
                interest == self.interest and locked == self.locked:
            return False
        self.available = available
        self.total = total
        self.borrowed = borrowed
        self.interest = interest
        self.locked = locked
        return True

    def reset(self):
        """
        Reset asset portfolio to zero
        """
        self.set(available=constants.ZERO, total=constants.ZERO, borrowed=constants.ZERO,
                 interest=constants.ZERO, locked=constants.ZERO)
