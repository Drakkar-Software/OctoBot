import typing

import octobot_commons.profiles.profile_data as profile_data_import
import octobot_commons.constants
import octobot_trading.enums as trading_enums

import octobot_flow.entities
import octobot_flow.logic.dsl

import tentacles.Meta.Keywords.scripting_library as scripting_library


def create_profile_data(
    exchange_account_details: typing.Optional[octobot_flow.entities.ExchangeAccountDetails],
    automation_id: str,
    symbols: set[str]
) -> profile_data_import.ProfileData:
    crypto_currencies = _get_crypto_currencies(symbols)
    return profile_data_import.ProfileData(
        profile_details=profile_data_import.ProfileDetailsData(
            bot_id=automation_id
        ),
        crypto_currencies=crypto_currencies,
        exchanges=[exchange_account_details.exchange_details] if exchange_account_details else [],
        trading=profile_data_import.TradingData(
            reference_market=_infer_reference_market(exchange_account_details, crypto_currencies) 
        ),
        trader_simulator=profile_data_import.TraderSimulatorData(
            enabled=exchange_account_details.is_simulated() if exchange_account_details else True,
        ),
        tentacles=[], # no tentacles: only the generic dsl executor will be used
    )

def _infer_reference_market(
    exchange_account_details: typing.Optional[octobot_flow.entities.ExchangeAccountDetails],
    crypto_currencies: list[profile_data_import.CryptoCurrencyData]) -> str:
    if (
        exchange_account_details
        and exchange_account_details.exchange_details.exchange_type == trading_enums.ExchangeTypes.FUTURE
    ):
        return octobot_commons.constants.DEFAULT_REFERENCE_MARKET
    if crypto_currencies:
        return octobot_commons.symbols.parse_symbol(crypto_currencies[0].trading_pairs[0]).quote # type: ignore
    elif exchange_account_details:
        return scripting_library.get_default_exchange_reference_market(exchange_account_details.exchange_details.internal_name)
    return octobot_commons.constants.DEFAULT_REFERENCE_MARKET

def _get_crypto_currencies(symbols: set[str]) -> list[profile_data_import.CryptoCurrencyData]:
    return [
        profile_data_import.CryptoCurrencyData(trading_pairs=[symbol], name=symbol)
        for symbol in symbols
    ]