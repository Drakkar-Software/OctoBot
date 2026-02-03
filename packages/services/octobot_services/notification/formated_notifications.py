#  Drakkar-Software OctoBot-Services
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
import abc

import octobot_commons.enums as common_enums
import octobot_commons.pretty_printer as pretty_printer

import octobot_trading.constants as constants

import octobot_services.notification as notifications
import octobot_services.enums as enums


class _OrderNotification(notifications.Notification):
    def __init__(self, text, evaluator_notification: notifications.Notification):
        super().__init__("", text, "", enums.NotificationSound.NO_SOUND,
                         common_enums.MarkdownFormat.IGNORE,
                         enums.NotificationLevel.INFO,
                         enums.NotificationCategory.TRADES,
                         evaluator_notification)
        self._build_text()

    @abc.abstractmethod
    def _build_text(self):
        raise NotImplementedError("_build_text is not implemented")


class OrderCreationNotification(_OrderNotification):
    def __init__(self, evaluator_notification: notifications.Notification, dict_order: dict, exchange_name: str):
        self.dict_order = dict_order
        self.exchange_name = exchange_name.capitalize()
        super().__init__("Order created", evaluator_notification)

    def _build_text(self):
        self.text = ""
        self.markdown_text = ""
        self.text += f"- {pretty_printer.open_order_pretty_printer(self.exchange_name, self.dict_order, markdown=False)}"
        self.markdown_text += \
            f"- {pretty_printer.open_order_pretty_printer(self.exchange_name, self.dict_order, markdown=True)}"


class OrderEndNotification(_OrderNotification):
    def __init__(self, order_previous_notification: notifications.Notification,
                 dict_order_filled: dict, exchange_name: str,
                 dict_orders_canceled: list, trade_profitability: float, portfolio_profitability: float,
                 portfolio_diff: float, add_profitability: bool, is_simulated: bool):
        self.dict_order_filled = dict_order_filled
        self.exchange_name = exchange_name.capitalize()
        self.dict_orders_canceled = dict_orders_canceled
        self.trade_profitability = trade_profitability
        self.portfolio_profitability = portfolio_profitability
        self.portfolio_diff = portfolio_diff
        self.add_profitability = add_profitability
        self.is_simulated = is_simulated
        super().__init__("Order update", order_previous_notification)

    def _build_text(self):
        self.text = ""
        self.markdown_text = ""
        trader_type = constants.SIMULATOR_TRADER_STR if self.is_simulated else constants.REAL_TRADER_STR
        if self.dict_order_filled is not None:
            self.text += f"{trader_type}Order(s) filled : " \
                         f"\n- {pretty_printer.open_order_pretty_printer(self.exchange_name, self.dict_order_filled)}"
            md_text = pretty_printer.open_order_pretty_printer(self.exchange_name, self.dict_order_filled, markdown=True)
            self.markdown_text += f"*{trader_type}*Order(s) filled : \n-{md_text}"

        if self.dict_orders_canceled is not None and self.dict_orders_canceled:
            self.text += f"{trader_type}Order(s) canceled :"
            self.markdown_text += f"*{trader_type}*Order(s) canceled :"
            for dict_order in self.dict_orders_canceled:
                self.text += f"\n- {pretty_printer.open_order_pretty_printer(self.exchange_name, dict_order)}"
                self.markdown_text += \
                    f"\n- {pretty_printer.open_order_pretty_printer(self.exchange_name, dict_order, markdown=True)}"

        if self.trade_profitability is not None and self.add_profitability:
            self.text += f"\nTrade profitability : {'+' if self.trade_profitability >= 0 else ''}" \
                         f"{round(self.trade_profitability, 4)}%"
            self.markdown_text += f"\nTrade profitability : *{'+' if self.trade_profitability >= 0 else ''}" \
                                  f"{round(self.trade_profitability, 4)}%*"

        if self.portfolio_profitability is not None and self.add_profitability:
            self.text += f"\nPortfolio profitability : {round(self.portfolio_profitability, 4)}% " \
                         f"{'+' if self.portfolio_diff >= 0 else ''}{round(self.portfolio_diff, 4)}%"
            self.markdown_text += f"\nPortfolio profitability : `{round(self.portfolio_profitability, 4)}% " \
                                  f"{'+' if self.portfolio_diff >= 0 else ''}{round(self.portfolio_diff, 4)}%`"
