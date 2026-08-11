import typing

import octobot_commons.profiles.profile_data as profile_data_import
import octobot_commons.constants
import octobot_protocol.models as protocol_models
import octobot_trading.enums as trading_enums
import octobot_trading.util.protocol_trading_mapping as protocol_trading_mapping

import octobot_flow.entities

import tentacles.Meta.Keywords.scripting_library as scripting_library


def profile_data_for_account(
    account: protocol_models.Account,
    exchange_account: protocol_models.ExchangeAccount,
    exchange_config: protocol_models.ExchangeConfig,
    trading_type: protocol_models.TradingType,
    *,
    is_simulated: bool,
) -> profile_data_import.ProfileData:
    profile_data = profile_data_import.ProfileData(
        exchanges=[
            profile_data_import.ExchangeData(
                internal_name=exchange_config.exchange,
                exchange_type=protocol_trading_mapping.TRADING_TYPE_TO_EXCHANGE_TYPE.get(trading_type).value,
                exchange_account_id=exchange_account.remote_account_id or account.id,
                sandboxed=exchange_config.sandboxed,
            )
        ]
    )
    profile_data.trader.enabled = not is_simulated
    profile_data.trader_simulator.enabled = is_simulated
    return profile_data


def _tentacles_for_exchange_account_details(
    exchange_account_details: typing.Optional[octobot_flow.entities.ExchangeAccountDetails],
) -> list[profile_data_import.TentaclesData]:
    if exchange_account_details is None:
        return []
    exchange_details = exchange_account_details.exchange_details
    if exchange_details.url:
        from tentacles.Trading.Exchange.hollaex import hollaex as hollaex_exchange_class
        if exchange_details.internal_name == hollaex_exchange_class.get_name():
            return [
                hollaex_exchange_class.get_tentacles_data_exchange_config(
                    exchange_details.internal_name,
                    exchange_details.url,
                )
            ]
    return []


def create_profile_data(
    exchange_account_details: typing.Optional[octobot_flow.entities.ExchangeAccountDetails],
    automation_id: str,
    symbols: set[str],
    as_simulator: typing.Optional[bool] = None,
) -> profile_data_import.ProfileData:
    crypto_currencies = _get_crypto_currencies(symbols)
    return profile_data_import.ProfileData(
        profile_details=profile_data_import.ProfileDetailsData(
            bot_id=automation_id
        ),
        crypto_currencies=crypto_currencies,
        exchanges=[exchange_account_details.exchange_details] if exchange_account_details else [],
        trading=profile_data_import.TradingData(
            reference_market=infer_reference_market(exchange_account_details, crypto_currencies) 
        ),
        trader_simulator=profile_data_import.TraderSimulatorData(
            enabled=as_simulator if as_simulator is not None else (
                exchange_account_details.is_simulated() if exchange_account_details else True
            )
        ),
        tentacles=_tentacles_for_exchange_account_details(exchange_account_details),
    )

def infer_reference_market(
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
        if exchange_account_details.portfolio.unit:
            # portfolio unit can be used to define the reference market
            return exchange_account_details.portfolio.unit
        return scripting_library.get_default_exchange_reference_market(exchange_account_details.exchange_details.internal_name)
    return octobot_commons.constants.DEFAULT_REFERENCE_MARKET

def _get_crypto_currencies(symbols: set[str]) -> list[profile_data_import.CryptoCurrencyData]:
    return [
        profile_data_import.CryptoCurrencyData(trading_pairs=[symbol], name=symbol)
        for symbol in symbols
    ]