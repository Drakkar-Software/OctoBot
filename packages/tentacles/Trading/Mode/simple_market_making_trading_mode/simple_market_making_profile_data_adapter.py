#  Drakkar-Software OctoBot-Commons
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
import typing

import octobot_commons.constants
import octobot_commons.profiles
import octobot_commons.profiles.profile_data
import octobot_commons.profiles.exchange_auth_data
import octobot_commons.symbols as symbols_util
import octobot_commons.logging as commons_logging
import octobot_trading.constants
import octobot.automation.automation as automation_module
import octobot.community.supabase_backend.enums as community_enums

import tentacles.Automation.trigger_events.volatility_threshold_event.volatility_threshold as volatility_threshold_module
import tentacles.Automation.trigger_events.holding_threshold_event.holding_threshold as holding_threshold_module
import tentacles.Automation.conditions.no_condition_condition.no_condition as no_condition_module
import tentacles.Automation.actions.stop_strategies_and_pause_trader_action.stop_strategies_and_pause_trader as stop_action_module
import tentacles.Meta.Keywords.scripting_library as scripting_library
import tentacles.Trading.Exchange as tentacles_exchanges
import tentacles.Trading.Mode.simple_market_making_trading_mode as simple_market_making_trading_mode

try:
    import tentacles.Meta.Keywords.business_bot_community_library as business_bot_community_library
except ImportError:
    # do not block import when business bot community library is not available
    business_bot_community_library = None

EXCHANGE_CONFIGS = "exchange_configs"
NAME = "name"
EXCHANGE_CREDENTIAL_ID = "exchange_credential_id"
EXCHANGE_ACCOUNT_ID = "exchange_account_id"
SANDBOXED = "sandboxed"
EXCHANGE_TYPE = "exchange_type"
URL = "url"


class SimpleMarketMakingProfileDataAdapter(octobot_commons.profiles.TentaclesProfileDataAdapter):
    async def adapt(
        self,
        profile_data: octobot_commons.profiles.ProfileData,
        auth_data: list[octobot_commons.profiles.exchange_auth_data.ExchangeAuthData]
    ) -> None:
        exchange_configs: typing.Optional[list] = None
        if self.additional_data:
            exchange_configs = self.additional_data.get(
                community_enums.BotConfigKeys.EXCHANGES.value
            )
            if not exchange_configs:
                if options := self.additional_data.get(
                    community_enums.BotConfigKeys.OPTIONS.value
                ):
                    if legacy_exchange_configs := options.get(EXCHANGE_CONFIGS):
                        exchange_configs = legacy_exchange_configs
                        commons_logging.get_logger(self.__class__.__name__).warning(
                            f"Using legacy exchange configs stored in options: {exchange_configs}"
                        )
        is_simulated = bool(
            self.additional_data.get(
                community_enums.BotConfigKeys.IS_SIMULATED.value,
                False,
            )
        ) if self.additional_data else False
        can_trade = True # init at True to allow predicted book calls
        if profile_data.profile_details.bot_id:
            # this is a running bot, check if it can trade
            if self.authenticator.user_account.bot_id != profile_data.profile_details.bot_id:
                await self.authenticator.select_bot(profile_data.profile_details.bot_id)
            can_trade = await self.authenticator.community_bot.should_trade_according_to_products_subscription_and_deployment_error_status()
        if not can_trade:
            commons_logging.get_logger(self.__class__.__name__).error(
                f"Bot should not be running: desired status is stopped, clearing traded currencies "
                f"config to avoid trading: trader will be paused"
            )
        profile_data.trading.paused = not can_trade # pause trading if bot should not be running
        mm_tentacle_config = self._get_simple_market_making_tentacle_config()
        # traded pairs are taken from market making configured pairs
        pair_configs = mm_tentacle_config[simple_market_making_trading_mode.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS]
        traded_pairs = list(set(
            pairs_config[simple_market_making_trading_mode.SimpleMarketMakingTradingMode.CONFIG_PAIR]
            for pairs_config in pair_configs
        ))
        profile_data.crypto_currencies += [
            octobot_commons.profiles.profile_data.CryptoCurrencyData([traded_pair], name=traded_pair)
            for traded_pair in traded_pairs
        ] if can_trade else []
        if traded_pairs:
            # reference market is the most common usd-like element of traded pairs
            try:
                profile_data.trading.reference_market = symbols_util.get_most_common_usd_like_symbol(traded_pairs)
            except ValueError:
                # no common USD-like pair: use 1st pair quote asset
                profile_data.trading.reference_market = symbols_util.parse_symbol(traded_pairs[0]).quote # type: ignore
        # exchanges are taken from exchange_configs and market making reference prices
        exchange_auth_data_by_name = {
            exchange_config[NAME]: octobot_commons.profiles.ExchangeAuthData(
                internal_name=exchange_config[NAME],
                exchange_credential_id=exchange_config.get(EXCHANGE_CREDENTIAL_ID),
                sandboxed=exchange_config.get(SANDBOXED, False),
                exchange_type=exchange_config.get(EXCHANGE_TYPE, octobot_commons.constants.DEFAULT_EXCHANGE_TYPE),
            )
            for exchange_config in exchange_configs
        } if exchange_configs else {}
        exchange_account_id_by_name = {
            exchange_config[NAME]: exchange_config.get(EXCHANGE_ACCOUNT_ID)
            for exchange_config in exchange_configs
        } if exchange_configs else {}
        if exchange_configs is None:
            if not profile_data.exchanges:
                raise ValueError(
                    "No exchanges found in profile data and no exchange "
                    "configs provided in additional data"
                )
        else:
            # configure exchanges from exchange auth data and reference price exchanges
            profile_data.exchanges = [
                octobot_commons.profiles.profile_data.ExchangeData(
                    internal_name=auth_data.internal_name,
                    exchange_account_id=exchange_account_id_by_name.get(auth_data.internal_name),
                )
                for auth_data in exchange_auth_data_by_name.values()
            ]
            reference_price_exchanges = set(
                ref_exchange[simple_market_making_trading_mode.SimpleMarketMakingTradingMode.EXCHANGE]
                for pair_config in pair_configs
                for ref_exchange in pair_config[
                    simple_market_making_trading_mode.SimpleMarketMakingTradingMode.REFERENCE_PRICE
                ]
                if ref_exchange[simple_market_making_trading_mode.SimpleMarketMakingTradingMode.EXCHANGE] !=
                simple_market_making_trading_mode.SimpleMarketMakingTradingMode.LOCAL_EXCHANGE_PRICE
            )
            profile_data.exchanges += [
                octobot_commons.profiles.profile_data.ExchangeData(internal_name=exchange)
                for exchange in reference_price_exchanges
                if exchange not in exchange_auth_data_by_name
            ]
            # register auto-filled exchange config if any
            self._register_exchange_configs(profile_data, exchange_configs)

        # register automations config
        self._register_automations_config(profile_data, pair_configs)

        # ensure all required fields are present
        for tentacle_config in self.tentacles_data:
            if tentacle_config.name == simple_market_making_trading_mode.SimpleMarketMakingTradingMode.get_name():
                tentacle_config.config[octobot_trading.constants.TRADING_MODE_REQUIRED_STRATEGIES] = (
                    tentacle_config.config.get(octobot_trading.constants.TRADING_MODE_REQUIRED_STRATEGIES, [])
                )

        # register tentacles config
        profile_data.tentacles += self.tentacles_data

        # trading type
        profile_data.trader.enabled = not is_simulated
        profile_data.trader_simulator.enabled = is_simulated

        # should not happen in real environment
        if is_simulated:
            if not octobot_commons.constants.IS_DEV_MODE_ENABLED:
                raise ValueError("Simulator configuration is not supported")
            max_funds_by_symbol = {}
            for pair_config in pair_configs:
                parsed_pair = symbols_util.parse_symbol(
                    pair_config[simple_market_making_trading_mode.SimpleMarketMakingTradingMode.CONFIG_PAIR]
                )
                if max_base_funds := pair_config[
                    simple_market_making_trading_mode.SimpleMarketMakingTradingMode.MAX_BASE_BUDGET
                ]:
                    max_funds_by_symbol[parsed_pair.base] = max_base_funds
                if max_quote_funds := pair_config[
                    simple_market_making_trading_mode.SimpleMarketMakingTradingMode.MAX_QUOTE_BUDGET
                ]:
                    max_funds_by_symbol[parsed_pair.quote] = max_quote_funds
            default_value = 100000
            logger = commons_logging.get_logger(self.__class__.__name__)
            for traded_pair in traded_pairs:
                parsed_pair = symbols_util.parse_symbol(traded_pair)
                base_funds = max_funds_by_symbol.get(parsed_pair.base, default_value)
                logger.info(f"Using {base_funds} {parsed_pair.base} in simulated portfolio")
                profile_data.trader_simulator.starting_portfolio[parsed_pair.base] = (base_funds)
                quote_funds = max_funds_by_symbol.get(parsed_pair.quote, default_value)
                logger.info(f"Using {quote_funds} {parsed_pair.quote} in simulated portfolio")
                profile_data.trader_simulator.starting_portfolio[parsed_pair.quote] = (quote_funds)
        elif self._should_fill_exchange_auth():
            await self._add_exchange_auth(profile_data, auth_data, list(exchange_auth_data_by_name.values()))

    def _register_exchange_configs(
        self,
        profile_data: octobot_commons.profiles.ProfileData,
        exchange_configs: typing.Iterable[dict]
    ):
        for exchange_config in exchange_configs:
            exchange_url = exchange_config.get(URL)
            requires_auth = (
                self.exchange_config_requires_exchange_auth(exchange_config) 
                and bool(
                    exchange_config.get(EXCHANGE_ACCOUNT_ID) or # business API: bound to an exchange account
                    exchange_config.get(EXCHANGE_CREDENTIAL_ID) # cloud bots: bound to creds
                )
            )
            if exchange_url or requires_auth:
                exchange_config_update = {}
                if requires_auth:
                    exchange_config_update = {
                        octobot_commons.constants.CONFIG_FORCE_AUTHENTICATION: True
                    }
                if exchange_url:
                    exchange_tentacle_name = tentacles_exchanges.HollaexAutofilled.get_name()
                    tentacle_config = {**exchange_config_update, **{
                        tentacles_exchanges.HollaexAutofilled.AUTO_FILLED_KEY: {
                            profile_data.exchanges[0].internal_name: {
                                tentacles_exchanges.HollaexAutofilled.URL_KEY: exchange_url
                            }
                        }
                    }}
                else:
                    exchange_tentacle_name = scripting_library.get_exchange_tentacle_from_name(exchange_config[NAME]).__name__
                    tentacle_config = exchange_config_update
                profile_data.tentacles.append(
                    octobot_commons.profiles.profile_data.TentaclesData(
                        exchange_tentacle_name, tentacle_config
                    )
                )

    @staticmethod
    def _get_pair_exchange_name(pair_config: dict, profile_data: octobot_commons.profiles.ProfileData) -> str:
        for exchange_config in profile_data.exchanges:
            exchange_name = exchange_config.internal_name
            if exchange_name and simple_market_making_trading_mode.SimpleMarketMakingTradingMode.is_exchange_compatible_pair_setting(
                pair_config, exchange_name
            ):
                return exchange_name
        raise ValueError(f"No exchange found for pair config: {pair_config}")
    
    def _register_automations_config(
        self,
        profile_data: octobot_commons.profiles.ProfileData,
        pair_configs: typing.Iterable[dict]
    ):
        automations = {}

        for pair_config in pair_configs:
            exchange_name = self._get_pair_exchange_name(
                pair_config, profile_data
            )
            conditions_configs = pair_config.get("stop_conditions")
            if not conditions_configs:
                continue
            traded_pair = pair_config[simple_market_making_trading_mode.SimpleMarketMakingTradingMode.CONFIG_PAIR]
            parsed_symbol = symbols_util.parse_symbol(traded_pair)

            self._parse_volatility_threshold_automation(
                automations, conditions_configs, exchange_name, traded_pair
            )
            self._parse_holding_threshold_automations(
                automations, conditions_configs, exchange_name, parsed_symbol
            )

        if automations:
            profile_data.tentacles.append(
                octobot_commons.profiles.profile_data.TentaclesData(
                    name=automation_module.Automation.get_name(),
                    config={
                        automation_module.Automation.AUTOMATIONS_COUNT: len(automations),
                        automation_module.Automation.AUTOMATIONS: automations,
                    }
                )
            )

    @staticmethod
    def _create_stop_automation_entry(trigger_name: str, trigger_config: dict) -> dict:
        _NoCondition = no_condition_module.NoCondition
        _StopAction = stop_action_module.StopStrategiesAndPauseTrader
        _Automation = automation_module.Automation
        return {
            _Automation.TRIGGER_EVENT: trigger_name,
            trigger_name: trigger_config,
            _Automation.CONDITIONS: [_NoCondition.get_name()],
            _NoCondition.get_name(): {},
            _Automation.ACTIONS: [_StopAction.get_name()],
            _StopAction.get_name(): {},
        }

    @staticmethod
    def _parse_volatility_threshold_automation(
        automations: dict,
        conditions_configs: dict,
        exchange_name: str,
        traded_pair: str,
    ) -> None:
        _VolatilityThreshold = volatility_threshold_module.VolatilityThreshold
        # constants from legacy SimpleMarketMakingTradingMode config keys
        max_positive = conditions_configs.get("max_positive_percent_price_change", 0)
        max_negative = conditions_configs.get("max_negative_percent_price_change", 0)
        if max_positive or max_negative:
            _SMM = simple_market_making_trading_mode.SimpleMarketMakingTradingMode
            if _SMM.AVERAGE_PRICE_COUNTED_MINUTES in conditions_configs:
                period = conditions_configs[_SMM.AVERAGE_PRICE_COUNTED_MINUTES]
            elif _SMM.LEGACY_AVERAGE_PRIVE_COUNTED_MINUTES_KEY in conditions_configs:
                period = conditions_configs[_SMM.LEGACY_AVERAGE_PRIVE_COUNTED_MINUTES_KEY]
            else:
                period = 60
            automations[str(len(automations) + 1)] = (
                SimpleMarketMakingProfileDataAdapter._create_stop_automation_entry(
                    _VolatilityThreshold.get_name(),
                    {
                        _VolatilityThreshold.EXCHANGE: exchange_name,
                        _VolatilityThreshold.SYMBOL: traded_pair,
                        _VolatilityThreshold.PERIOD_IN_MINUTES: period,
                        _VolatilityThreshold.MAX_ALLOWED_POSITIVE_PERCENTAGE_CHANGE: max_positive,
                        _VolatilityThreshold.MAX_ALLOWED_NEGATIVE_PERCENTAGE_CHANGE: max_negative,
                    },
                )
            )

    @staticmethod
    def _parse_holding_threshold_automations(
        automations: dict,
        conditions_configs: dict,
        exchange_name: str,
        parsed_symbol: symbols_util.Symbol,
    ) -> None:
        _HoldingThreshold = holding_threshold_module.HoldingThreshold
        # constants from legacy SimpleMarketMakingTradingMode config keys
        for asset_attr in ["base", "quote"]:
            if amount := conditions_configs.get(f"min_{asset_attr}_holding", 0):
                automations[str(len(automations) + 1)] = (
                    SimpleMarketMakingProfileDataAdapter._create_stop_automation_entry(
                        _HoldingThreshold.get_name(),
                        {
                            _HoldingThreshold.EXCHANGE: exchange_name,
                            _HoldingThreshold.ASSET_NAME: getattr(parsed_symbol, asset_attr),
                            _HoldingThreshold.AMOUNT: amount,
                            _HoldingThreshold.STOP_ON_INFERIOR: True,
                        },
                    )
                )

    @staticmethod
    def requires_exchange_auth(exchange_configs: typing.Iterable[dict]) -> bool:
        for exchange_config in exchange_configs:
            if SimpleMarketMakingProfileDataAdapter.exchange_config_requires_exchange_auth(exchange_config):
                return True
        return False

    @staticmethod
    def exchange_config_requires_exchange_auth(exchange_config: dict) -> bool:
        return scripting_library.is_exchange_with_different_public_data_after_auth(exchange_config.get(NAME))

    def _should_fill_exchange_auth(self) -> bool:
        return bool(self.auth_key)

    async def _add_exchange_auth(
        self,
        profile_data: octobot_commons.profiles.ProfileData,
        auth_data: list[octobot_commons.profiles.exchange_auth_data.ExchangeAuthData],
        base_exchange_auth_datas: list[octobot_commons.profiles.exchange_auth_data.ExchangeAuthData],
    ):
        if profile_data.exchanges and not self.auth_key:
            raise ValueError(f"auth key is required to fetch exchange credentials")
        exchange_account_id_by_exchange_name = {
            exchange_data.internal_name: exchange_data.exchange_account_id
            for exchange_data in profile_data.exchanges
        }
        for base_exchange_auth_data in base_exchange_auth_datas:
            if business_bot_community_library is None:
                # TODO implement auth fetch
                raise ImportError("Business bot community library is not available")
            if fetched_auth_data := await business_bot_community_library.fetch_exchange_auth_data(
                self.authenticator,
                base_exchange_auth_data,
                exchange_account_id_by_exchange_name.get(base_exchange_auth_data.internal_name),
                self.authenticator.get_logged_in_email(),
                self.auth_key,
            ):
                auth_data.append(fetched_auth_data)
            else:
                commons_logging.get_logger(self.__class__.__name__).error(
                    f"Incomplete exchange auth data for {base_exchange_auth_data.internal_name} "
                )

    def _get_simple_market_making_tentacle_config(self) -> dict:
        for tentacle_data in self.tentacles_data:
            if tentacle_data.name == simple_market_making_trading_mode.SimpleMarketMakingTradingMode.get_name():
                return tentacle_data.config
        raise KeyError(
            f"{simple_market_making_trading_mode.SimpleMarketMakingTradingMode.get_name()} tentacle config not found"
        )

    @classmethod
    def get_tentacle_name(cls) -> str:
        return simple_market_making_trading_mode.SimpleMarketMakingTradingMode.get_name()
