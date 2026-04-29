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
import datetime
import flask

import octobot_services.interfaces.util as interfaces_util
import octobot_commons.constants as commons_constants
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models
import octobot_trading.api as trading_api


def register(blueprint):
    @blueprint.route("/symbol_market_status")
    @blueprint.route('/symbol_market_status', methods=['GET', 'POST'])
    @login.login_required_when_activated
    def symbol_market_status():
        exchange_id = flask.request.args["exchange_id"]
        symbol = flask.request.args["symbol"]
        symbol_time_frames, exchange = models.get_exchange_watched_time_frames(exchange_id)
        time_frames = list(symbol_time_frames)
        time_frames.reverse()
        symbol_evaluation = models.get_evaluation(symbol, exchange, exchange_id)
        return flask.render_template('symbol_market_status.html',
                                     symbol=symbol,
                                     exchange=exchange,
                                     exchange_id=exchange_id,
                                     symbol_evaluation=symbol_evaluation,
                                     time_frames=time_frames,
                                     backtesting_mode=models.get_in_backtesting_mode())


    @blueprint.route("/trading")
    @login.login_required_when_activated
    def trading():
        displayed_portfolio = models.get_exchange_holdings_per_symbol()
        has_real_trader, has_simulated_trader = interfaces_util.has_real_and_or_simulated_traders()
        symbols_values = models.get_symbols_values(displayed_portfolio.keys(), has_real_trader, has_simulated_trader) \
            if displayed_portfolio else {}
        has_real_trader, _ = interfaces_util.has_real_and_or_simulated_traders()
        exchanges_load = models.get_exchanges_load()
        pnl_symbols = models.get_pnl_history_symbols()
        return flask.render_template(
            'trading.html',
            might_have_positions=models.has_futures_exchange(),
            watched_symbols=models.get_watched_symbols(),
            pairs_with_status=interfaces_util.get_currencies_with_status(),
            displayed_portfolio=displayed_portfolio,
            symbols_values=symbols_values,
            has_real_trader=has_real_trader,
            exchanges_load=exchanges_load,
            is_community_feed_connected=models.is_community_feed_connected(),
            last_signal_time=models.get_last_signal_time(),
            followed_strategy_url=models.get_followed_strategy_url(),
            reference_market=interfaces_util.get_reference_market(),
            pnl_symbols=pnl_symbols,
            has_pnl_history=bool(pnl_symbols),
        )


    @blueprint.route("/trading_type_selector")
    @login.login_required_when_activated
    def trading_type_selector():
        onboarding = flask.request.args.get("onboarding", 'false').lower() == "true"
        display_config = interfaces_util.get_edited_config()

        config_exchanges = display_config[commons_constants.CONFIG_EXCHANGES]
        enabled_exchanges = trading_api.get_enabled_exchanges_names(display_config) or [models.get_default_exchange()]

        current_profile = models.get_current_profile()

        return_val = flask.render_template(
            'trading_type_selector.html',
            show_nab_bar=not onboarding,
            onboarding=onboarding,

            current_profile_name=current_profile.name,
            config_exchanges=config_exchanges,
            enabled_exchanges=enabled_exchanges,
            exchanges_details=models.get_exchanges_details(config_exchanges),
            ccxt_tested_exchanges=models.get_tested_exchange_list(),
            ccxt_simulated_tested_exchanges=models.get_simulated_exchange_list(),
            ccxt_other_exchanges=sorted(models.get_other_exchange_list()),

            simulated_portfolio=models.get_json_simulated_portfolio(display_config),
            portfolio_schema=models.JSON_PORTFOLIO_SCHEMA,
            real_trader_activated=models.is_real_trading(current_profile),
        )
        return return_val


    @blueprint.context_processor
    def utility_processor():
        def convert_timestamp(str_time):
            return datetime.datetime.fromtimestamp(str_time).strftime('%Y-%m-%d %H:%M:%S')

        def convert_type(order_type):
            return order_type.name

        return dict(convert_timestamp=convert_timestamp, convert_type=convert_type)
