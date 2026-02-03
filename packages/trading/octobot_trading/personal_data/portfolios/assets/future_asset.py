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


class FutureAsset(asset_class.Asset):
    def __init__(self, name, available, total,
                 initial_margin=constants.ZERO,
                 wallet_balance=constants.ZERO,
                 position_margin=constants.ZERO,
                 order_margin=constants.ZERO,
                 unrealized_pnl=constants.ZERO):
        """
        Future Asset
        :param name: the asset name
        :param available: the margin available (wallet balance - used margin)
        :param total: the margin balance (wallet balance + unrealized PNL)
        :param initial_margin: the total initial margin required with current mark price
        :param wallet_balance: the wallet balance
        :param position_margin: margin required for positions with current mark price
        :param order_margin: margin required for open orders with current mark price
        :param unrealized_pnl: the unrealized profit and loss
        """
        super().__init__(name, available, total)
        # Unrealized profit and loss
        self.unrealized_pnl: decimal.Decimal = unrealized_pnl

        # total initial margin required with current mark price
        self.initial_margin: decimal.Decimal = initial_margin

        # The Wallet balance. When using Cross Margin, the number minus the unclosed loss is the real wallet balance.
        self.wallet_balance: decimal.Decimal = wallet_balance if wallet_balance != constants.ZERO else total

        # margin required for positions with current mark price
        self.position_margin: decimal.Decimal = position_margin

        # margin required for open orders with current mark price
        self.order_margin: decimal.Decimal = order_margin

    def __str__(self):
        return super().__str__() + " | " \
                                   f"Initial Margin: {float(self.initial_margin)} | " \
                                   f"Wallet Balance: {float(self.wallet_balance)} | " \
                                   f"Unrealized PNL: {float(self.unrealized_pnl)} | " \
                                   f"Order Margin: {float(self.order_margin)} | " \
                                   f"Position Margin: {float(self.position_margin)}"

    def __eq__(self, other):
        if isinstance(other, FutureAsset):
            return self.available == other.available and self.total == other.total and \
                   self.initial_margin == other.initial_margin and self.wallet_balance == other.wallet_balance and \
                   self.position_margin == other.position_margin and self.order_margin == other.order_margin
        return False

    def _specific_restore_unavailable_from_other(self, other_asset):
        if other_asset.initial_margin != constants.ZERO:
            self.initial_margin = self.initial_margin + other_asset.initial_margin
        # update wallet_balance when handling cross positions
        if other_asset.position_margin != constants.ZERO:
            self.position_margin = self.position_margin + other_asset.position_margin
        if other_asset.order_margin != constants.ZERO:
            self.order_margin = self.order_margin + other_asset.order_margin
    
    def get_total_holdings(self):
        """
        Get the total holdings of the asset: in futures, this is the wallet balance
        :return: the total holdings
        """
        return self.wallet_balance


    def restore(self, old_asset):
        """
        Restore asset from previous state
        :param old_asset: previous asset state
        """
        super().restore(old_asset)
        self.unrealized_pnl = old_asset.unrealized_pnl
        self.initial_margin = old_asset.initial_margin
        self.wallet_balance = old_asset.wallet_balance
        self.position_margin = old_asset.position_margin
        self.order_margin = old_asset.order_margin

    def update(self, total=constants.ZERO, available=constants.ZERO, position_margin=constants.ZERO,
               unrealized_pnl=constants.ZERO, initial_margin=constants.ZERO):
        """
        Update asset portfolio
        :param total: the wallet balance delta
        :param initial_margin: the initial margin delta
        :param position_margin: the position margin delta
        :param available: the order margin delta
        :param unrealized_pnl: the unrealized pnl delta
        :return: True if updated
        """
        if available == constants.ZERO and position_margin == constants.ZERO \
                and total == constants.ZERO and unrealized_pnl == constants.ZERO:
            return False

        with self.update_or_restore():
            self.initial_margin += self._ensure_update_validity(self.initial_margin, initial_margin)
            self.position_margin = self._ensure_not_negative(self.position_margin + position_margin)
            self.order_margin = self._ensure_not_negative(self.order_margin + available)
            self.unrealized_pnl += unrealized_pnl
            self.wallet_balance += self._ensure_update_validity(self.wallet_balance, total)
            self._update_available()
            self._update_total()
            return True

    def set(self, total=constants.ZERO, available=None, initial_margin=constants.ZERO, position_margin=constants.ZERO,
            unrealized_pnl=constants.ZERO, order_margin=constants.ZERO, margin_balance=None):
        """
        Set available, total, initial_margin, wallet_balance, position_margin and maintenance_margin
        values for portfolio asset
        :param total: the wallet balance value
        :param available: the available margin balance value
        :param initial_margin: the initial margin value
        :param position_margin: the position margin value
        :param unrealized_pnl: the unrealized pnl value
        :param order_margin: the order margin value
        :param margin_balance: the margin balance value
        :return: True if updated
        """
        if position_margin == self.position_margin and order_margin == self.order_margin \
                and total == self.wallet_balance:
            return False

        with self.update_or_restore():
            self.initial_margin = initial_margin
            self.position_margin = position_margin
            self.order_margin = order_margin
            self.unrealized_pnl = unrealized_pnl
            self.wallet_balance = total
            if available is not None:
                self.available = available
            else:
                self._update_available()
            if margin_balance is not None:
                self.total = margin_balance
            else:
                self._update_total()
            return True

    def set_unrealized_pnl(self, unrealized_pnl):
        """
        Sets the unrealized pnl value and updates the total (margin balance) value
        :param unrealized_pnl: the new unrealized pnl value
        """
        self.unrealized_pnl = unrealized_pnl
        self._update_total()

    def update_realised_pnl(self, realized_pnl_update):
        """
        Updates the realized pnl value
        :param realized_pnl_update: the realized pnl update
        """
        self.wallet_balance += self._ensure_update_validity(self.wallet_balance, realized_pnl_update)
        self._update_total()
        self._update_available()

    def reset(self):
        """
        Reset asset portfolio to zero
        """
        self.set(total=constants.ZERO, available=constants.ZERO,
                 initial_margin=constants.ZERO, margin_balance=constants.ZERO,
                 unrealized_pnl=constants.ZERO, order_margin=constants.ZERO, position_margin=constants.ZERO)

    def _update_total(self):
        """
        Update total (margin balance) value with wallet balance + unrealized pnl
        """
        self.total = self._ensure_update_validity(constants.ZERO, self.wallet_balance + self.unrealized_pnl)

    def _update_available(self):
        """
        Update available (margin available) value with wallet balance - used margin
        """
        self.available = self._ensure_update_validity(constants.ZERO,
                                                      self.wallet_balance - self.position_margin - self.order_margin)
