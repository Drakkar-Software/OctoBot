# pylint: disable=C0103,R0902,C0301
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
import copy
import dataclasses
import typing

import octobot_commons.profiles.profile as profile_import
import octobot_commons.dataclasses
import octobot_commons.constants as constants


@dataclasses.dataclass
class ProfileDetailsData(
    octobot_commons.dataclasses.FlexibleDataclass,
    octobot_commons.dataclasses.UpdatableDataclass,
):
    name: str = ""
    id: typing.Union[str, None] = None
    bot_id: typing.Union[str, None] = None
    version: typing.Union[str, None] = None
    user_id: typing.Union[str, None] = None
    nested_strategy_config_id: typing.Union[str, None] = None


@dataclasses.dataclass
class CryptoCurrencyData(
    octobot_commons.dataclasses.FlexibleDataclass,
    octobot_commons.dataclasses.UpdatableDataclass,
):
    trading_pairs: list[str] = dataclasses.field(default_factory=list)
    name: typing.Union[str, None] = None
    enabled: bool = True


@dataclasses.dataclass
class ExchangeData(
    octobot_commons.dataclasses.FlexibleDataclass,
    octobot_commons.dataclasses.UpdatableDataclass,
):
    exchange_credential_id: typing.Union[str, None] = (
        None  # deprecated, use exchange_account_id instead, exchange_credential_id is updated in exchange_data.auth_details
    )
    internal_name: typing.Union[str, None] = None
    exchange_type: str = constants.DEFAULT_EXCHANGE_TYPE
    exchange_id: typing.Union[str, None] = None
    exchange_account_id: typing.Union[str, None] = None
    sandboxed: bool = False


@dataclasses.dataclass
class FutureSymbolData(
    octobot_commons.dataclasses.FlexibleDataclass,
    octobot_commons.dataclasses.UpdatableDataclass,
):
    symbol: typing.Optional[str] = None
    leverage: typing.Union[float, None] = None


@dataclasses.dataclass
class FutureExchangeData(
    octobot_commons.dataclasses.FlexibleDataclass,
    octobot_commons.dataclasses.UpdatableDataclass,
):
    default_leverage: typing.Union[float, None] = None
    symbol_data: list[FutureSymbolData] = dataclasses.field(default_factory=list)

    # pylint: disable=E1134
    def __post_init__(self):
        if self.symbol_data and isinstance(self.symbol_data[0], dict):
            self.symbol_data = [
                FutureSymbolData.from_dict(symbol_datum)
                for symbol_datum in self.symbol_data
            ]


@dataclasses.dataclass
class TraderData(
    octobot_commons.dataclasses.FlexibleDataclass,
    octobot_commons.dataclasses.UpdatableDataclass,
):
    enabled: bool = True


@dataclasses.dataclass
class TraderSimulatorData(
    octobot_commons.dataclasses.FlexibleDataclass,
    octobot_commons.dataclasses.UpdatableDataclass,
):
    enabled: bool = False
    starting_portfolio: dict[str, float] = dataclasses.field(default_factory=dict)
    maker_fees: float = 0.1
    taker_fees: float = 0.1


@dataclasses.dataclass
class MinimalFund(
    octobot_commons.dataclasses.FlexibleDataclass,
    octobot_commons.dataclasses.UpdatableDataclass,
):
    asset: typing.Optional[str] = None
    available: typing.Optional[float] = None
    total: typing.Optional[float] = None

    @classmethod
    def from_dict(cls, dict_value: dict):
        to_use_dict = copy.copy(dict_value)
        if "value" in dict_value:
            if "available" not in dict_value:
                to_use_dict["available"] = dict_value["value"]
            if "total" not in dict_value:
                to_use_dict["total"] = dict_value["value"]
        return super().from_dict(to_use_dict)


@dataclasses.dataclass
class TradingData(
    octobot_commons.dataclasses.FlexibleDataclass,
    octobot_commons.dataclasses.UpdatableDataclass,
):
    reference_market: str = ""
    minimal_funds: list[MinimalFund] = dataclasses.field(default_factory=list)
    risk: float = 1.0
    sub_portfolio: dict[str, float] = dataclasses.field(default_factory=dict)
    sellable_assets: typing.Optional[list[str]] = None
    paused: bool = False

    # pylint: disable=E1134
    def __post_init__(self):
        if self.minimal_funds and isinstance(self.minimal_funds[0], dict):
            self.minimal_funds = [
                MinimalFund.from_dict(minimal_fund)
                for minimal_fund in self.minimal_funds
            ]


@dataclasses.dataclass
class TentaclesData(
    octobot_commons.dataclasses.FlexibleDataclass,
    octobot_commons.dataclasses.UpdatableDataclass,
):
    name: typing.Optional[str] = None
    config: dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class BacktestingContext(
    octobot_commons.dataclasses.FlexibleDataclass,
    octobot_commons.dataclasses.UpdatableDataclass,
):
    start_time_delta: float = 0
    update_interval: float = 7 * constants.DAYS_TO_SECONDS
    starting_portfolio: dict = dataclasses.field(default_factory=dict)
    exchanges: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class OptionsData(
    octobot_commons.dataclasses.FlexibleDataclass,
    octobot_commons.dataclasses.UpdatableDataclass,
):
    values: dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class ProfileData(
    octobot_commons.dataclasses.MinimizableDataclass,
    octobot_commons.dataclasses.UpdatableDataclass,
):
    profile_details: ProfileDetailsData = dataclasses.field(
        default_factory=ProfileDetailsData
    )
    crypto_currencies: list[CryptoCurrencyData] = dataclasses.field(
        default_factory=list
    )
    trading: TradingData = dataclasses.field(default_factory=TradingData)
    exchanges: list[ExchangeData] = dataclasses.field(default_factory=list)
    future_exchange_data: FutureExchangeData = dataclasses.field(
        default_factory=FutureExchangeData
    )
    trader: TraderData = dataclasses.field(default_factory=TraderData)
    trader_simulator: TraderSimulatorData = dataclasses.field(
        default_factory=TraderSimulatorData
    )
    tentacles: list[TentaclesData] = dataclasses.field(default_factory=list)
    backtesting_context: BacktestingContext = dataclasses.field(
        default_factory=BacktestingContext
    )
    options: OptionsData = dataclasses.field(default_factory=OptionsData)
    distribution: str = constants.DEFAULT_DISTRIBUTION

    # pylint: disable=E1134
    def __post_init__(self):
        if self.crypto_currencies and isinstance(self.crypto_currencies[0], dict):
            self.crypto_currencies = [
                CryptoCurrencyData.from_dict(crypto_currency)
                for crypto_currency in self.crypto_currencies
            ]
        if self.exchanges and isinstance(self.exchanges[0], dict):
            self.exchanges = [
                ExchangeData.from_dict(exchange) for exchange in self.exchanges
            ]
        if self.tentacles and isinstance(self.tentacles[0], dict):
            self.tentacles = (
                [TentaclesData.from_dict(tentacle) for tentacle in self.tentacles]
                if self.tentacles
                else []
            )

    @classmethod
    def from_profile(cls, profile: profile_import.Profile):
        """
        Creates a cls instance from the given profile
        """
        profile_dict = profile.as_dict()
        content = profile_dict[constants.PROFILE_CONFIG]
        return cls.from_dict(
            {
                "profile_details": {
                    "id": profile_dict[constants.CONFIG_PROFILE][constants.CONFIG_ID],
                    "name": profile_dict[constants.CONFIG_PROFILE][
                        constants.CONFIG_NAME
                    ],
                },
                "crypto_currencies": [
                    {
                        "trading_pairs": details.get(constants.CONFIG_CRYPTO_PAIRS, []),
                        "name": currency,
                        "enabled": details.get(constants.CONFIG_ENABLED_OPTION, True),
                    }
                    for currency, details in content[
                        constants.CONFIG_CRYPTO_CURRENCIES
                    ].items()
                ],
                "trader": {
                    "enabled": content[constants.CONFIG_TRADER][
                        constants.CONFIG_ENABLED_OPTION
                    ],
                },
                "trader_simulator": {
                    "enabled": content[constants.CONFIG_SIMULATOR][
                        constants.CONFIG_ENABLED_OPTION
                    ],
                    "starting_portfolio": content[constants.CONFIG_SIMULATOR][
                        constants.CONFIG_STARTING_PORTFOLIO
                    ],
                    "maker_fees": content[constants.CONFIG_SIMULATOR][
                        constants.CONFIG_SIMULATOR_FEES
                    ].get(constants.CONFIG_SIMULATOR_FEES_MAKER, 0.0),
                    "taker_fees": content[constants.CONFIG_SIMULATOR][
                        constants.CONFIG_SIMULATOR_FEES
                    ].get(constants.CONFIG_SIMULATOR_FEES_TAKER, 0.0),
                },
                "trading": {
                    "reference_market": content[constants.CONFIG_TRADING][
                        constants.CONFIG_TRADER_REFERENCE_MARKET
                    ],
                    "risk": content[constants.CONFIG_TRADING][
                        constants.CONFIG_TRADER_RISK
                    ],
                },
                "tentacles": [],
            }
        )

    def to_profile(self, to_create_profile_path: str) -> profile_import.Profile:
        """
        Returns a new Profile from self
        """
        profile = profile_import.Profile(to_create_profile_path)
        profile.from_dict(self._to_profile_dict())
        return profile

    def set_tentacles_config(self, config_by_tentacle: dict):
        """
        Update self.tentacles from the given config_by_tentacle
        """
        self.tentacles = [
            TentaclesData(name=tentacle, config=config)
            for tentacle, config in config_by_tentacle.items()
        ]

    def _to_profile_dict(self) -> dict:
        return {
            constants.PROFILE_CONFIG: {
                constants.CONFIG_CRYPTO_CURRENCIES: {
                    crypto_currency.name: {
                        constants.CONFIG_CRYPTO_PAIRS: crypto_currency.trading_pairs,
                        constants.CONFIG_ENABLED_OPTION: crypto_currency.enabled,
                    }
                    for crypto_currency in self.crypto_currencies
                },
                constants.CONFIG_EXCHANGES: {
                    exchange_details.internal_name: {
                        constants.CONFIG_ENABLED_OPTION: True,
                        constants.CONFIG_EXCHANGE_TYPE: exchange_details.exchange_type,
                    }
                    for exchange_details in self.exchanges
                },
                constants.CONFIG_TRADER: {
                    constants.CONFIG_ENABLED_OPTION: self.trader.enabled,
                    constants.CONFIG_LOAD_TRADE_HISTORY: True,
                },
                constants.CONFIG_SIMULATOR: {
                    constants.CONFIG_ENABLED_OPTION: self.trader_simulator.enabled,
                    constants.CONFIG_STARTING_PORTFOLIO: self.trader_simulator.starting_portfolio
                    or (
                        self.backtesting_context.starting_portfolio
                        if self.backtesting_context
                        else {}
                    ),
                    constants.CONFIG_SIMULATOR_FEES: {
                        constants.CONFIG_SIMULATOR_FEES_MAKER: self.trader_simulator.maker_fees,
                        constants.CONFIG_SIMULATOR_FEES_TAKER: self.trader_simulator.taker_fees,
                    },
                },
                constants.CONFIG_TRADING: {
                    constants.CONFIG_TRADER_REFERENCE_MARKET: self.trading.reference_market,
                    constants.CONFIG_TRADER_RISK: self.trading.risk,
                    constants.CONFIG_TRADER_PAUSED: self.trading.paused,
                },
                constants.CONFIG_DISTRIBUTION: self.distribution,
            },
            constants.CONFIG_PROFILE: dataclasses.asdict(self.profile_details),
        }
