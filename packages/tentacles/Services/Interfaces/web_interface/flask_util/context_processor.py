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
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.constants as commons_constants
import octobot_commons.authentication as authentication
import octobot.constants as constants
import octobot.enums as enums
import octobot.community.identifiers_provider as identifiers_provider
import octobot.community.supabase_backend.enums as community_enums
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.models.configuration as configuration_model
import tentacles.Services.Interfaces.web_interface.enums as web_enums
import tentacles.Services.Interfaces.web_interface as web_interface
import tentacles.Services.Interfaces.web_interface.constants as web_constants
import tentacles.Services.Interfaces.web_interface.login as web_interface_login
import octobot_services.interfaces as interfaces
import octobot_trading.util as trading_util
import octobot_trading.api as trading_api
import octobot_trading.enums as trading_enums


def register_context_processor(web_interface_instance):
    @web_interface_instance.server_instance.context_processor
    def context_processor_register():
        def get_color_mode() -> str:
            return models.get_color_mode().value

        def get_distribution() -> str:
            return models.get_distribution().value

        def get_tentacle_config_file_content(tentacle_class):
            return models.get_tentacle_config(tentacle_class)

        def get_exchange_holdings(holdings, holding_type):
            return ', '.join(f'{exchange.capitalize()}: {holding[holding_type]}'
                             for exchange, holding in holdings['exchanges'].items())

        def _get_details_from_full_symbol_list(full_symbol_list, currency_name):
            for symbol_details in full_symbol_list:
                if symbol_details[configuration_model.SHORT_NAME_KEY].lower() == currency_name:
                    return symbol_details
            raise KeyError(currency_name)

        def get_currency_id(full_symbol_list, currency_name):
            currency_key = currency_name.lower()
            try:
                return _get_details_from_full_symbol_list(full_symbol_list, currency_key)[configuration_model.ID_KEY]
            except KeyError:
                return currency_key

        def filter_currency_pairs(currency, symbol_list_by_type, full_symbol_list, config_symbols):
            currency_key = currency.lower()
            try:
                symbol = _get_details_from_full_symbol_list(full_symbol_list, currency_key)[configuration_model.SYMBOL_KEY]
            except KeyError:
                return symbol_list_by_type
            filtered_symbol = {
                symbol_type: [
                    s
                    for s in symbols
                    if symbol in symbol_util.parse_symbol(s).base_and_quote()
                ]
                for symbol_type, symbols in symbol_list_by_type.items()
            }
            for symbol_type in list(filtered_symbol.keys()):
                filtered_symbol[symbol_type] += [
                    s
                    for s in config_symbols[currency][commons_constants.CONFIG_CRYPTO_PAIRS]
                    if s in symbol_list_by_type[symbol_type] and s not in filtered_symbol[symbol_type]
                ]
            return filtered_symbol

        def get_profile_traded_pairs_by_currency(profile):
            return {
                currency: val[commons_constants.CONFIG_CRYPTO_PAIRS]
                for currency, val in profile.config[commons_constants.CONFIG_CRYPTO_CURRENCIES].items()
                if commons_constants.CONFIG_CRYPTO_PAIRS in val
                    and val[commons_constants.CONFIG_CRYPTO_PAIRS]
                    and trading_util.is_currency_enabled(profile.config, currency, True)
            }

        def get_profile_exchanges(profile):
            return trading_api.get_enabled_exchanges_names(profile.config)

        def is_supporting_future_trading(supported_exchange_types):
            return trading_enums.ExchangeTypes.FUTURE in supported_exchange_types

        def get_enabled_trader(profile):
            if models.is_real_trading(profile):
                return "Real trading"
            if trading_util.is_trader_simulator_enabled(profile.config):
                return "Simulated trading"
            return ""

        def get_filtered_list(origin_list, filtering_list):
            return [
                element
                for element in origin_list
                if element in filtering_list
            ]

        def get_plugin_tabs(location):
            has_open_source_package = models.has_open_source_package()
            for plugin in web_interface_instance.registered_plugins:
                for tab in plugin.get_tabs():
                    if tab.location is location and tab.is_available(has_open_source_package):
                        yield tab

        def is_in_stating_community_env():
            return identifiers_provider.IdentifiersProvider.ENABLED_ENVIRONMENT is enums.CommunityEnvironments.Staging

        def get_enabled_tentacles(tentacles_info_by_name):
            for name, info in tentacles_info_by_name:
                if info[web_constants.ACTIVATION_KEY]:
                    return name

        def get_logged_in_email():
            try:
                return authentication.Authenticator.instance().get_logged_in_email()
            except (authentication.AuthenticationRequired, authentication.UnavailableError):
                return ""

        current_profile = models.get_current_profile()
        trading_mode = models.get_config_activated_trading_mode()
        selected_bot = models.get_selected_user_bot()
        selected_bot_id = (selected_bot.get(community_enums.BotKeys.ID.value) or "") if selected_bot else ""


        return dict(
            LAST_UPDATED_STATIC_FILES=web_interface.LAST_UPDATED_STATIC_FILES,
            OCTOBOT_WEBSITE_URL=constants.OCTOBOT_WEBSITE_URL,
            OCTOBOT_DOCS_URL=constants.OCTOBOT_DOCS_URL,
            DEVELOPER_DOCS_URL=constants.DEVELOPER_DOCS_URL,
            EXCHANGES_DOCS_URL=constants.EXCHANGES_DOCS_URL,
            OCTOBOT_FEEDBACK_URL=constants.OCTOBOT_FEEDBACK,
            OCTOBOT_EXTENSION_PACKAGE_1_NAME=constants.OCTOBOT_EXTENSION_PACKAGE_1_NAME,
            OCTOBOT_COMMUNITY_URL=identifiers_provider.IdentifiersProvider.COMMUNITY_URL,
            OCTOBOT_COMMUNITY_RECOVER_PASSWORD_URL=identifiers_provider.IdentifiersProvider.FRONTEND_PASSWORD_RECOVER_URL,
            OCTOBOT_MARKET_MAKING_URL=constants.OCTOBOT_MARKET_MAKING_URL,
            CURRENT_BOT_VERSION=interfaces.AbstractInterface.project_version,
            LOCALE=constants.DEFAULT_LOCALE,
            IS_DEMO=constants.IS_DEMO,
            IS_CLOUD=constants.IS_CLOUD_ENV,
            CAN_INSTALL_TENTACLES=constants.CAN_INSTALL_TENTACLES,
            IS_ALLOWING_TRACKING=models.get_metrics_enabled(),
            PH_TRACKING_ID=constants.PH_TRACKING_ID,
            USER_EMAIL=get_logged_in_email(),
            USER_SELECTED_BOT_ID=selected_bot_id,
            PROFILE_NAME=current_profile.name,
            TRADING_MODE_NAME=trading_mode.get_name() if trading_mode else "",
            EXCHANGE_NAMES=",".join(get_profile_exchanges(current_profile)),
            IS_REAL_TRADING=models.is_real_trading(current_profile),
            TAB_START=web_enums.TabsLocation.START,
            TAB_END=web_enums.TabsLocation.END,
            get_color_mode=get_color_mode,
            get_distribution=get_distribution,
            get_tentacle_config_file_content=get_tentacle_config_file_content,
            get_currency_id=get_currency_id,
            filter_currency_pairs=filter_currency_pairs,
            get_exchange_holdings=get_exchange_holdings,
            get_profile_traded_pairs_by_currency=get_profile_traded_pairs_by_currency,
            get_profile_exchanges=get_profile_exchanges,
            get_enabled_trader=get_enabled_trader,
            get_filtered_list=get_filtered_list,
            get_current_profile=models.get_current_profile,
            get_plugin_tabs=get_plugin_tabs,
            get_enabled_tentacles=get_enabled_tentacles,
            is_real_trading=models.is_real_trading,
            is_supporting_future_trading=is_supporting_future_trading,
            is_login_required=web_interface_login.is_login_required,
            is_authenticated=web_interface_login.is_authenticated,
            is_in_stating_community_env=is_in_stating_community_env,
            startup_messages=models.get_startup_messages(),
            are_automations_enabled=models.are_automations_enabled(),
            is_backtesting_enabled=models.is_backtesting_enabled(),
            is_advanced_interface_enabled=models.is_advanced_interface_enabled(),
            has_open_source_package=models.has_open_source_package,
            critical_notifications=web_interface.get_critical_notifications(),
        )
