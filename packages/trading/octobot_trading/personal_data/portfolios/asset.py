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
import contextlib
import copy
import decimal

import octobot_commons.constants as common_constants
import octobot_commons.logging as logging

import octobot_trading.constants as constants
import octobot_trading.errors as errors


class Asset:
    def __init__(self, name, available, total):
        self.name: str = name

        self.available: decimal.Decimal = available
        self.total: decimal.Decimal = total

    def __str__(self):
        return f"{self.__class__.__name__}: {self.name} | " \
               f"Available: {float(self.available)} | " \
               f"Total: {float(self.total)}"

    def __repr__(self):
        # __repr__ is called when a dict is turned into string (like in logs)
        return str(self)

    def __eq__(self, other):
        raise NotImplementedError("__eq__ is not implemented")

    def update(self, **kwargs):
        """
        Update asset portfolio
        :return: True if updated
        """
        raise NotImplementedError("update is not implemented")

    def set(self, **kwargs):
        """
        Set portfolio asset
        :return: True if updated
        """
        raise NotImplementedError("set is not implemented")

    def restore_available(self):
        """
        Balance available value with total
        """
        self.available = self.total

    def restore_unavailable_from_other(self, other_asset):
        with self.update_or_restore():
            if other_asset.available < other_asset.total:
                self.available = self.available - (other_asset.total - other_asset.available)
            self._specific_restore_unavailable_from_other(other_asset)

    def _specific_restore_unavailable_from_other(self, other_asset):
        """
        Implement if necessary
        """

    def reset(self):
        """
        Reset asset portfolio to zero
        """
        raise NotImplementedError("reset is not implemented")

    def restore(self, old_asset):
        """
        Restore asset from previous state
        :param old_asset: previous asset state
        """
        self.name = old_asset.name
        self.available = old_asset.available
        self.total = old_asset.total

    def to_dict(self):
        """
        :return: asset to dictionary
        """
        return {
            common_constants.PORTFOLIO_AVAILABLE: self.available,
            common_constants.PORTFOLIO_TOTAL: self.total
        }

    def _ensure_update_validity(self, origin_quantity, update_quantity):
        """
        Ensure that the portfolio final value is not negative.
        Raise a PortfolioNegativeValueError if the final value is negative
        :param origin_quantity: the original currency value
        :param update_quantity: the update value
        :return: the updated quantity
        """
        if origin_quantity + update_quantity < constants.ZERO:
            raise errors.PortfolioNegativeValueError(f"Trying to update {self.name} with {update_quantity} "
                                                     f"but quantity was {origin_quantity}")
        return update_quantity

    def _ensure_not_negative(self, new_value, replacement_value=constants.ZERO):
        """
        Ensure that the new asset value is not negative
        When new value is negative return replacement_value
        :param new_value: the value to check
        :param replacement_value: the replacement value when new value is negative
        :return: the new value if not negative else the replacement value
        """
        if new_value > constants.ZERO:
            return new_value
        return replacement_value

    @contextlib.contextmanager
    def update_or_restore(self):
        """
        Ensure update complete without raising PortfolioNegativeValueError else restore Asset instance's attributes
        """
        previous_asset = copy.copy(self)
        try:
            yield
        except errors.PortfolioNegativeValueError:
            logging.get_logger(self.__class__.__name__).info("Restoring after PortfolioNegativeValueError...")
            self.restore(previous_asset)
            raise
    
    def get_total_holdings(self):
        """
        Get the total holdings of the asset
        :return: the total holdings
        """
        return self.total
