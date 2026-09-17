import typing

import octobot_commons
import octobot_commons.profiles.profile_data as profile_data_import
import octobot_commons.constants
import octobot_commons.symbols as commons_symbols
import octobot_protocol.models as protocol_models
import octobot_trading.enums as trading_enums
import octobot_trading.api.exchange as exchange_api
import octobot_trading.util.protocol_trading_mapping as protocol_trading_mapping

import octobot_flow.entities


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
    if exchange_account_details and exchange_account_details.portfolio.unit:
        return exchange_account_details.portfolio.unit
    if crypto_currencies:
        return _portfolio_asset_from_trading_pair_symbol(crypto_currencies[0].trading_pairs[0], leg="quote")
    if exchange_account_details and exchange_account_details.exchange_details.internal_name:
        return exchange_api.get_default_exchange_reference_market(
            exchange_account_details.exchange_details.internal_name
        )
    return octobot_commons.constants.DEFAULT_REFERENCE_MARKET


def _portfolio_asset_from_trading_pair_symbol(symbol: str, *, leg: typing.Literal["base", "quote"]) -> str:
    parsed = commons_symbols.parse_symbol(symbol)
    if parsed.has_ticker_wise_networks():
        currency = parsed.base if leg == "base" else parsed.quote
        network = parsed.base_network if leg == "base" else parsed.quote_network
        return f"{currency}{octobot_commons.NETWORK_SEPARATOR}{network}"
    if leg == "base":
        return parsed.base
    return parsed.quote  # type: ignore[return-value]


def _get_crypto_currencies(symbols: set[str]) -> list[profile_data_import.CryptoCurrencyData]:
    trading_pairs_by_base: dict[str, list[str]] = {}
    for symbol in symbols:
        base_currency = _portfolio_asset_from_trading_pair_symbol(symbol, leg="base")
        trading_pairs_by_base.setdefault(base_currency, []).append(symbol)
    return [
        profile_data_import.CryptoCurrencyData(trading_pairs=trading_pairs, name=base_currency)
        for base_currency, trading_pairs in sorted(trading_pairs_by_base.items())
    ]