import enum

import octobot_trading.exchanges as trading_exchanges

import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.spot_hedging_engine as spot_hedging_engine
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.hedging_engine as hedging_engine
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.errors as hedging_errors


_HEDGING_ENGINES_HEDGING_EXCHANGE_NAME_BY_TRADING_EXCHANGE_ID: dict[str, dict[str, hedging_engine.HedgingEngine]] = {}


class HedgingEngineTypes(enum.Enum):
    SPOT = "spot"
    PERPETUAL_FUTURES = "perpetual_futures"


def hedging_engine_type_factory(hedging_engine_type: HedgingEngineTypes) -> type[hedging_engine.HedgingEngine]:
    if hedging_engine_type == HedgingEngineTypes.SPOT:
        return spot_hedging_engine.SpotHedgingEngine
    elif hedging_engine_type == HedgingEngineTypes.PERPETUAL_FUTURES:
        raise NotImplementedError("Perpetual futures hedging engine is not implemented yet")
    raise ValueError(f"Invalid hedging engine type: {hedging_engine_type}")


def get_or_create_hedging_engine(
    hedging_engine_type: HedgingEngineTypes,
    trading_exchange_manager: trading_exchanges.ExchangeManager,
    hedging_exchange_name: str
) -> hedging_engine.HedgingEngine:
    # Create on one hedging engine per hedging exchange and trading exchange
    # in order to handle multi-symbol trading
    if trading_exchange_manager.id not in _HEDGING_ENGINES_HEDGING_EXCHANGE_NAME_BY_TRADING_EXCHANGE_ID:
        _HEDGING_ENGINES_HEDGING_EXCHANGE_NAME_BY_TRADING_EXCHANGE_ID[trading_exchange_manager.id] = {
            hedging_exchange_name: hedging_engine_type_factory(hedging_engine_type)(
                trading_exchange_manager, hedging_exchange_name
            )
        }
    if hedging_exchange_name not in _HEDGING_ENGINES_HEDGING_EXCHANGE_NAME_BY_TRADING_EXCHANGE_ID[trading_exchange_manager.id]:
        conflicting_hedging_exchange = next(iter(_HEDGING_ENGINES_HEDGING_EXCHANGE_NAME_BY_TRADING_EXCHANGE_ID[trading_exchange_manager.id]))
        raise hedging_errors.HedgingExchangeConflictError(
            f"Hedging engine for trading exchange [{trading_exchange_manager.exchange_name} with id {trading_exchange_manager.id}] "
            f"using [{hedging_exchange_name}] as hedging exchange can't be started because "
            f"[{conflicting_hedging_exchange}] is already hedging this exchange"
        )
    candidate_hedging_engine = _HEDGING_ENGINES_HEDGING_EXCHANGE_NAME_BY_TRADING_EXCHANGE_ID[trading_exchange_manager.id][hedging_exchange_name]
    if isinstance(candidate_hedging_engine, hedging_engine_type_factory(hedging_engine_type)):
        # ensure a different hedging engine type is not asked for when re-using an existing hedging engine
        return candidate_hedging_engine
    raise hedging_errors.HedgingExchangeConflictError(
        f"Hedging engine for trading exchange [{trading_exchange_manager.exchange_name} with id {trading_exchange_manager.id}] "
        f"is a {type(candidate_hedging_engine).__name__} but a {hedging_engine_type_factory(hedging_engine_type).__name__} is asked for."
    )
