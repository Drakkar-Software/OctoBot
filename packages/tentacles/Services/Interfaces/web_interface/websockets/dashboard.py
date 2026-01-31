#  Drakkar-Software OctoBot-Tentacles
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

import flask_socketio

import octobot_commons.pretty_printer as pretty_printer
import octobot_trading.enums as trading_enums
import octobot_services.interfaces as services_interfaces
import octobot_trading.api as octobot_trading_api
import tentacles.Services.Interfaces.web_interface as web_interface
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.websockets as websockets


class DashboardNamespace(websockets.AbstractWebSocketNamespaceNotifier):

    @staticmethod
    def _get_profitability():
        profitability_digits = None
        has_real_trader, has_simulated_trader, \
        real_global_profitability, simulated_global_profitability, \
        real_percent_profitability, simulated_percent_profitability, \
        real_no_trade_profitability, simulated_no_trade_profitability, \
        market_average_profitability = services_interfaces.get_global_profitability()
        profitability_data = {
            "market_average_profitability": pretty_printer.round_with_decimal_count(market_average_profitability,
                                                                                    profitability_digits)
        }
        if has_real_trader:
            profitability_data["bot_real_profitability"] = \
                pretty_printer.round_with_decimal_count(real_percent_profitability, profitability_digits)
            profitability_data["bot_real_flat_profitability"] = \
                pretty_printer.round_with_decimal_count(real_global_profitability, profitability_digits)
            profitability_data["real_no_trade_profitability"] = \
                pretty_printer.round_with_decimal_count(real_no_trade_profitability, profitability_digits)
        if has_simulated_trader:
            profitability_data["bot_simulated_profitability"] = \
                pretty_printer.round_with_decimal_count(simulated_percent_profitability, profitability_digits)
            profitability_data["bot_simulated_flat_profitability"] = \
                pretty_printer.round_with_decimal_count(simulated_global_profitability, profitability_digits)
            profitability_data["simulated_no_trade_profitability"] = \
                pretty_printer.round_with_decimal_count(simulated_no_trade_profitability, profitability_digits)
        return profitability_data

    @staticmethod
    def _format_new_data(exchange_id=None, trades=None, order=None, symbol=None):
        exchange_manager = octobot_trading_api.get_exchange_manager_from_exchange_id(exchange_id)
        return {
            "trades": models.format_trades(trades),
            "orders": models.format_orders(octobot_trading_api.get_open_orders(exchange_manager, symbol=symbol), 0),
            "simulated": octobot_trading_api.is_trader_simulated(exchange_manager),
            "symbol": symbol,
            "exchange_id": exchange_id
        }

    @websockets.websocket_with_login_required_when_activated
    def on_profitability(self):
        flask_socketio.emit("profitability", self._get_profitability())

    def all_clients_send_notifications(self, **kwargs) -> bool:
        if self._has_clients():
            try:
                self.socketio.emit("new_data",
                                   {
                                       "data": self._format_new_data(**kwargs)
                                   },
                                   namespace=self.namespace)
                return True
            except Exception as e:
                self.logger.exception(e, True, f"Error when sending web notification: {e}")
        return False

    @websockets.websocket_with_login_required_when_activated
    def on_candle_graph_update(self, data):
        try:
            flask_socketio.emit("candle_graph_update_data", {
                "request": data,
                "data": models.get_currency_price_graph_update(data["exchange_id"],
                                                               models.get_value_from_dict_or_string(data["symbol"]),
                                                               data["time_frame"],
                                                               backtesting=False,
                                                               minimal_candles=True,
                                                               ignore_trades=True,
                                                               ignore_orders=not models.get_display_orders())
            })
        except KeyError:
            flask_socketio.emit("error", "missing exchange manager")

    @websockets.websocket_with_login_required_when_activated
    def on_connect(self):
        super().on_connect()
        self.on_profitability()


notifier = DashboardNamespace('/dashboard')
web_interface.register_notifier(web_interface.DASHBOARD_NOTIFICATION_KEY, notifier)
websockets.namespaces.append(notifier)
