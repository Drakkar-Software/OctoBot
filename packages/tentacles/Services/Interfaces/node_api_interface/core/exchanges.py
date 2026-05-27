import enum

import octobot_commons.constants as commons_constants
import octobot_commons.profiles.profile_data
import octobot_protocol.models as protocol_models
import octobot_trading.enums
import octobot_trading.exchanges
import octobot_trading.api
import octobot_tentacles_manager.api
import octobot.community.models.formatters as community_formatters


class ExchangeInfo(enum.Enum):
    PAIRS = "pairs"
    TIMEFRAMES = "timeframes"


def exchange_type_from_trading_type(trading_type: protocol_models.TradingType) -> str:
    return commons_constants.TRADING_TYPE_TO_EXCHANGE_TYPE[trading_type]


async def get_traded_pairs_and_timeframes_by_exchange(
    exchange_config: protocol_models.ExchangeConfig,
    trading_type: protocol_models.TradingType = protocol_models.TradingType.SPOT,
) -> dict[str, dict[str, list[str]]]:
    traded_pairs_and_tf_by_exchange = {}
    tentacles_setup_config = octobot_tentacles_manager.api.get_full_tentacles_setup_config()
    profile_data = _get_exchange_profile_data(exchange_config, trading_type=trading_type)
    for exchange in profile_data.exchanges:
        internal_name = exchange.internal_name
        local_exchange_type = octobot_trading.enums.ExchangeTypes(exchange.exchange_type)
        exchange_data = octobot_trading.exchanges.exchange_data_factory(
            internal_name,
            exchange_type=local_exchange_type.value
        )
        async with octobot_trading.exchanges.exchange_manager_from_exchange_data(
            exchange_data, profile_data, tentacles_setup_config, None
        ) as exchange_manager:
            traded_pairs_and_tf_by_exchange[internal_name] = {
                ExchangeInfo.PAIRS.value: list(
                    octobot_trading.api.get_all_available_symbols(exchange_manager, exchange_type=local_exchange_type)
                ),
                ExchangeInfo.TIMEFRAMES.value: list(
                    octobot_trading.api.get_all_available_time_frames(exchange_manager)
                ),
            }
    return traded_pairs_and_tf_by_exchange


def _get_exchange_profile_data(
    exchange_config: protocol_models.ExchangeConfig,
    trading_type: protocol_models.TradingType = protocol_models.TradingType.SPOT,
) -> octobot_commons.profiles.profile_data.ProfileData:
    tentacles_data = []
    local_name = community_formatters.to_bot_exchange_internal_name(exchange_config.exchange)
    if exchange_config.url:
        import tentacles.Trading.Exchange
        import tentacles.Meta.Keywords.scripting_library as scripting_library
        exchange_config_update = {}
        if scripting_library.is_exchange_with_different_public_data_after_auth(local_name):
            exchange_config_update[commons_constants.CONFIG_FORCE_AUTHENTICATION] = True
        exchange_tentacle_name = tentacles.Trading.Exchange.HollaexAutofilled.get_name()
        tentacle_config = {**exchange_config_update, **{
            tentacles.Trading.Exchange.HollaexAutofilled.AUTO_FILLED_KEY: {
                local_name: {
                    tentacles.Trading.Exchange.HollaexAutofilled.URL_KEY: exchange_config.url
                }
            }
        }}
        tentacles_data.append(octobot_commons.profiles.profile_data.TentaclesData(
            exchange_tentacle_name, tentacle_config
        ))
    return octobot_commons.profiles.profile_data.ProfileData(
        octobot_commons.profiles.profile_data.ProfileDetailsData(),
        [],
        octobot_commons.profiles.profile_data.TradingData(""),
        exchanges=[octobot_commons.profiles.profile_data.ExchangeData(
            internal_name=local_name,
            sandboxed=exchange_config.sandboxed,
            exchange_type=exchange_type_from_trading_type(trading_type),
        )],
        tentacles=tentacles_data
    )
