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
import flask

import octobot_services.interfaces.util as interfaces_util
import octobot_commons.constants as commons_constants
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models


def register(blueprint):
    @blueprint.route("/portfolio")
    @login.login_required_when_activated
    def portfolio():
        has_real_trader, has_simulated_trader = interfaces_util.has_real_and_or_simulated_traders()

        displayed_portfolio = models.get_exchange_holdings_per_symbol()
        symbols_values = models.get_symbols_values(displayed_portfolio.keys(), has_real_trader, has_simulated_trader) \
            if displayed_portfolio else {}

        _, _, portfolio_real_current_value, portfolio_simulated_current_value = \
            interfaces_util.get_portfolio_current_value()

        displayed_portfolio_value = portfolio_real_current_value if has_real_trader else portfolio_simulated_current_value
        reference_market = interfaces_util.get_reference_market()
        initializing_currencies_prices_set = models.get_initializing_currencies_prices_set(
            commons_constants.HOURS_TO_SECONDS
        )

        return flask.render_template('portfolio.html',
                                     has_real_trader=has_real_trader,
                                     has_simulated_trader=has_simulated_trader,
                                     displayed_portfolio=displayed_portfolio,
                                     symbols_values=symbols_values,
                                     displayed_portfolio_value=round(displayed_portfolio_value, 8),
                                     reference_unit=reference_market,
                                     initializing_currencies_prices=initializing_currencies_prices_set,
                                     )
