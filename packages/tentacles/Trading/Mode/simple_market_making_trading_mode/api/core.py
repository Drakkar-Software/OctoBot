import decimal
import time
import typing
import asyncio
import copy

import octobot_commons.profiles
import octobot_commons.constants
import octobot_commons.enums
import octobot_commons.errors
import octobot_commons.logging
import octobot_commons.profiles.profile_data
import octobot_commons.symbols as commons_symbols

import octobot_trading.api
import octobot_trading.enums
import octobot_trading.constants
import octobot_trading.errors
import octobot_trading.exchange_data
import octobot_trading.exchanges
import octobot_flow.entities
import octobot.community.supabase_backend.enums as community_enums

import octobot_tentacles_manager.api
import octobot_protocol.models.market_making_configuration as market_making_configuration_model

import tentacles.Services.Interfaces.node_api_interface.core.exchanges as exchanges_core
import tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_trading as \
    simple_market_making_trading
import tentacles.Trading.Mode.simple_market_making_trading_mode.advanced_reference_price as \
    advanced_reference_price_import
import tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter as \
    simple_market_making_profile_data_adapter
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.models as models
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.constants as constants



async def get_market_making_profile_data(
    exchange_configs: list[exchanges_core.ExchangeConfig], 
    market_making_config: typing.Optional[market_making_configuration_model.MarketMakingConfiguration],
    user_auth: typing.Optional[octobot_flow.entities.UserAuthentication]
) -> octobot_commons.profiles.ProfileData:
    if market_making_config:
        return await _get_market_making_profile_data(
            exchange_configs, market_making_config, user_auth
        )
    return await get_market_making_exchange_only_profile_data(exchange_configs, user_auth)


async def _fill_market_making_data_by_symbol(
    profile_data_template: octobot_commons.profiles.ProfileData,
    exchange_internal_name: str, sandboxed: bool, 
    price_sources: list[advanced_reference_price_import.AdvancedPriceSource],
    mm_data_by_symbol_by_exchange: dict[str, dict[str, models.MarketMakingData]],
    with_market_status: bool, auth: typing.Optional[octobot_flow.entities.UserAuthentication],
):
    profile_data = copy.deepcopy(profile_data_template)
    profile_data.exchanges[0].internal_name = exchange_internal_name # use local exchange name
    exchange_type = profile_data.exchanges[0].exchange_type \
        if profile_data.exchanges else octobot_commons.constants.DEFAULT_EXCHANGE_TYPE
    exchange_data = octobot_trading.exchanges.exchange_data_factory(exchange_internal_name, exchange_type=exchange_type)
    cached_tickers = octobot_trading.exchange_data.TickerUpdater.get_ticker_cache().get_all_tickers(
        exchange_internal_name, exchange_type, sandboxed
    )
    tickers = {}
    symbols = [source.pair for source in price_sources]
    dependency_symbols: set[str] = set()
    if cached_tickers:
        tickers = {
            symbol: ticker
            for symbol, ticker in cached_tickers.items()
            if symbol in symbols
        }
    missing_tickers = [symbol for symbol in symbols if symbol not in tickers]
    has_formula = any(source.formula for source in price_sources)
    dependency_symbol_alias_by_symbol: dict[str, typing.Optional[str]] = {}

    if has_formula or missing_tickers or not cached_tickers:
        tentacles_setup_config = octobot_tentacles_manager.api.get_full_tentacles_setup_config()
        async with octobot_trading.exchanges.exchange_manager_from_exchange_data(
            exchange_data, profile_data, tentacles_setup_config, None
        ) as exchange_manager:
            await octobot_trading.exchanges.create_temporary_exchange_channels_and_producers(
                exchange_manager,
                create_authenticated_producers=False,
            )
            dependencies = set()
            for source in price_sources:
                if source.formula:
                    try:
                        await source.initialize_if_required(exchange_manager)
                    except octobot_commons.errors.DSLInterpreterError as err:
                        raise ValueError(f"Invalid {source.pair} reference price formula: {err}") from err
                    dependencies.update(source.get_dependencies(exchange_manager))

            dependency_symbol_alias_by_symbol = {
                dependency.symbol: dependency.alias
                for dependency in dependencies
                if dependency.symbol
            }
            available_symbols = set(exchange_manager.exchange.get_all_available_symbols(active_only=True))
            symbols_to_skip_ticker_fetch = {
                source.pair
                for source in price_sources
                if source.formula and source.pair not in available_symbols
            }
            symbols_to_fetch = (set(symbols) | set(dependency_symbol_alias_by_symbol.keys())) - symbols_to_skip_ticker_fetch
            tickers = {
                symbol: ticker
                for symbol, ticker in tickers.items()
                if symbol in symbols_to_fetch
            }
            tickers, ticker_updater = await _fetch_tickers(
                exchange_manager, tickers, list(symbols_to_fetch)
            )
            if missing_tickers_to_fetch := [symbol for symbol in symbols_to_fetch if symbol not in tickers]:
                try:
                    tickers.update(await ticker_updater.fetch_all_tickers(missing_tickers_to_fetch))
                except octobot_trading.errors.NotSupported as err:
                    _get_logger().info(f"Fetching tickers for {missing_tickers_to_fetch} is not supported: {err}")

            to_fetch_candles_by_time_frame = {}
            for dependency in dependencies:
                if dependency.data_source == octobot_trading.constants.OHLCV_CHANNEL:
                    if dependency.time_frame not in to_fetch_candles_by_time_frame:
                        to_fetch_candles_by_time_frame[dependency.time_frame] = set()
                    to_fetch_candles_by_time_frame[dependency.time_frame].add(dependency.symbol)
            if to_fetch_candles_by_time_frame:
                ohlcv_updater = typing.cast(
                    octobot_trading.exchange_data.ohlcv.channel.OHLCVUpdater,
                    octobot_trading.api.get_channel_updater(
                        exchange_manager, octobot_trading.constants.OHLCV_CHANNEL
                    )
                )
                for time_frame, candle_symbols in to_fetch_candles_by_time_frame.items():
                    for symbol in candle_symbols:
                        ohlcvs = await ohlcv_updater.fetch_ohlcv(
                            symbol, octobot_commons.enums.TimeFrames(time_frame), 5, allow_cache=True, tickers_backup=tickers
                        )
                        exchange_data.markets.append(
                            octobot_trading.exchanges.MarketDetails.from_ohlcvs(symbol, time_frame, ohlcvs)
                        )
    market_statuses = {}
    all_symbols = set(symbols) | set(dependency_symbol_alias_by_symbol.keys())
    if with_market_status:
        tentacles_setup_config = octobot_tentacles_manager.api.get_full_tentacles_setup_config()
        async with octobot_trading.exchanges.exchange_manager_from_exchange_data(
            exchange_data, profile_data, tentacles_setup_config, None
        ) as exchange_manager:
            market_statuses.update({
                symbol: exchange_manager.exchange.get_market_status(symbol, with_fixer=False)
                for symbol in all_symbols
            })
    mm_data_by_symbol_by_exchange[exchange_internal_name] = {}
    for symbol in all_symbols:
        try:
            market_details = [
                market_detail
                for market_detail in exchange_data.markets
                if market_detail.symbol == symbol
            ]
            symbol_alias = dependency_symbol_alias_by_symbol.get(symbol)
            mm_data_by_symbol_by_exchange[exchange_internal_name][symbol] = _create_market_data(
                exchange_internal_name, symbol, symbol_alias, tickers.get(symbol), market_statuses, market_details
            )
        except decimal.DecimalException as err:
            _get_logger().exception(err, False)
            _get_logger().warning(f"Ignored market data for {symbol} ({err}), ticker={tickers.get(symbol)}")

async def _get_market_making_data_by_exchange(
    profile_data: octobot_commons.profiles.ProfileData,
    mm_exchanges: list[str],
    with_market_status: bool,
    user_auth: typing.Optional[octobot_flow.entities.UserAuthentication],
) -> dict[str, dict[str, models.MarketMakingData]]:
    aggregated_sources_by_exchange = get_aggregated_price_sources_by_exchange(
        profile_data, mm_exchanges
    )
    # fetch reference prices, volumes and symbol markets
    trading_exchanges = get_trading_exchanges(profile_data, mm_exchanges)
    mm_data_by_exchange: dict[str, dict[str, models.MarketMakingData]] = {}
    coros = [
        _fill_market_making_data_by_symbol(
            profile_data,
            exchange_internal_name,
            False,
            sources,
            mm_data_by_exchange,
            # fill market status on market making exchange only (skip it for price source exchanges)
            exchange_internal_name in trading_exchanges if with_market_status else False,
            user_auth,
        )
        for exchange_internal_name, sources in aggregated_sources_by_exchange.items()
        if sources
    ]
    if not coros:
        raise ValueError(
            "No market making volume to fetch. This usually means that the given configuration "
            "exchanges are empty or inconsistent."
        )
    await asyncio.gather(*coros)
    return mm_data_by_exchange


async def get_price_and_predicted_order_book(
    profile_data: octobot_commons.profiles.ProfileData, 
    user_auth: typing.Optional[octobot_flow.entities.UserAuthentication] = None,
) -> dict:
    mm_exchanges = [
        exchange.internal_name
        for exchange in profile_data.exchanges
    ]
    mm_data_by_exchange = await _get_market_making_data_by_exchange(profile_data, mm_exchanges, True, user_auth)
    return {
        exchange: await _get_price_and_predicted_order_book(
            profile_data, mm_data_by_exchange, exchange
        )
        for exchange in get_trading_exchanges(profile_data, mm_exchanges)
    }


async def update_liquidity_scores(
    profile_data: octobot_commons.profiles.profile_data.ProfileData,
    policy: models.OrderBookFetchPolicy,
    symbols: typing.Optional[list[str]] = None,
    custom_auth: typing.Optional[octobot_flow.entities.UserAuthentication] = None,
    user_auth: typing.Optional[octobot_flow.entities.UserAuthentication] = None,
) -> list[models.LiquidityScore]:
    liquidity_scores = []
    # async with (
    #     octobot.community.local_anon_user_authenticator() if custom_auth is None
    #     else octobot.community.local_user_authenticator(
    #         custom_auth.email, custom_auth.hidden,
    #         password=custom_auth.password, auth_key=custom_auth.auth_key
    #     )
    # ) as authenticator:
    for exchange in profile_data.exchanges:
        exchange_internal_name = exchange.internal_name
        try:
            # exchange_id = await kw_community.fetch_exchange_id(
            #     authenticator, exchange_internal_name, exchange.exchange_type
            # )
            exchange_id = "TODO" # todo: get exchange id from database when implemented
        except IndexError:
            raise ValueError(f"Exchange with internal name {exchange_internal_name} not found")
        exchange_data = octobot_trading.exchanges.exchange_data_factory(
            exchange_internal_name, exchange_type=exchange.exchange_type
        )
        local_profile_data = copy.copy(profile_data)
        local_profile_data.exchanges = [exchange]
        tentacles_setup_config = octobot_tentacles_manager.api.get_full_tentacles_setup_config()
        async with octobot_trading.exchanges.exchange_manager_from_exchange_data(
            exchange_data, local_profile_data, tentacles_setup_config, None
        ) as exchange_manager:
            await octobot_trading.exchanges.create_temporary_exchange_channels_and_producers(
                exchange_manager,
                create_authenticated_producers=False,
            )
            all_traded_symbols = octobot_trading.api.get_all_available_symbols(
                exchange_manager, octobot_trading.enums.ExchangeTypes(exchange_data.auth_details.exchange_type)
            )
            tickers, _ = await _fetch_tickers(
                exchange_manager, {}, list(all_traded_symbols)
            )
            to_update_symbols = get_symbols_to_fetch(policy, list(all_traded_symbols), symbols)
            if missing_data_symbols := [symbol for symbol in to_update_symbols if symbol not in tickers]:
                try:
                    # no ticker data: can't compute liquidity score
                    missing_data_liquidity_scores = get_missing_data_liquidity_scores(
                        exchange_id, missing_data_symbols
                    )
                    _get_logger().info(f"Upserting {len(missing_data_liquidity_scores)} missing data liquidity scores for {missing_data_symbols}")
                    # todo: upsert liquidity scores to database when implemented
                    # await kw_community.upsert_liquidity_scores(authenticator, missing_data_liquidity_scores)
                    liquidity_scores.extend(missing_data_liquidity_scores)
                except Exception as err:
                    _get_logger().exception(
                        err, True,
                        f"Unexpected error when computing [{exchange_internal_name}] fetching liquidity scores: "
                        f"{err}"
                    )
            books_to_fetch = [symbol for symbol in to_update_symbols if symbol in tickers]
            for book_size in (
                constants.BASE_ORDER_BOOK_FETCH_SIZE,
                constants.LARGER_ORDER_BOOK_FETCH_SIZE_BY_EXCHANGE.get(
                    exchange_internal_name, constants.DEFAULT_LARGER_ORDER_BOOK_FETCH_SIZE
                ) # type: ignore
            ):
                larger_books_to_fetch = []
                check_missing_data = (
                    book_size == constants.BASE_ORDER_BOOK_FETCH_SIZE
                    and octobot_trading.api.supports_custom_limit_order_book_fetch(exchange_manager)
                )
                if not books_to_fetch:
                    break
                async for symbol, order_book in _fetch_order_books(
                    exchange_manager, books_to_fetch, book_size
                ):
                    try:
                        liquidity_score = get_liquidity_score(
                            exchange_id, exchange_internal_name, symbol, tickers[symbol], order_book,
                            check_missing_data
                        )
                        # await kw_community.insert_liquidity_score(authenticator, liquidity_score)
                        # todo: insert liquidity score to database when implemented
                        _get_logger().info(f"Inserting liquidity score for {symbol} [{exchange_internal_name}]")
                        liquidity_scores.append(liquidity_score)
                    except octobot_trading.errors.MissingPriceDataError:
                        larger_books_to_fetch.append(symbol)
                    except Exception as err:
                        _get_logger().exception(
                            err, True,
                            f"Unexpected error when computing {symbol} [{exchange_internal_name}] liquidity score: "
                            f"{err}. Ignored pair."
                        )
                books_to_fetch = copy.copy(larger_books_to_fetch)
    return liquidity_scores


async def get_market_making_volume(
    profile_data: octobot_commons.profiles.ProfileData, 
    user_auth: typing.Optional[octobot_flow.entities.UserAuthentication] = None
) -> dict:
    mm_exchanges = [
        exchange.internal_name
        for exchange in profile_data.exchanges
    ]
    mm_data_by_exchange = await _get_market_making_data_by_exchange(
        profile_data, mm_exchanges, False, user_auth
    )
    market_making_volume_by_exchange = {}
    for mm_exchange in mm_exchanges:
        volume_by_symbol, error_by_symbol = (
            await get_minimal_volume_by_symbol(profile_data, mm_exchange, mm_data_by_exchange)
        )
        if formatted_volume := format_market_making_volume_by_symbol(
            volume_by_symbol, error_by_symbol
        ):
            market_making_volume_by_exchange[mm_exchange] = formatted_volume
    return market_making_volume_by_exchange


def get_market_making_trading_mode(market_making_trading_mode: str):
    return {
        simple_market_making_trading.SimpleMarketMakingTradingMode.get_name():
            simple_market_making_trading.SimpleMarketMakingTradingMode
    }[market_making_trading_mode]


def _create_profile_exchange_data(exchange_config: exchanges_core.ExchangeConfig) -> octobot_commons.profiles.profile_data.ExchangeData:
    return octobot_commons.profiles.profile_data.ExchangeData(
        internal_name=exchange_config.name,
        exchange_type=exchange_config.exchange_type if exchange_config.exchange_type else octobot_trading.enums.ExchangeTypes.SPOT.value,
        sandboxed=exchange_config.sandboxed,
    )


async def get_market_making_exchange_only_profile_data(
    exchange_configs: list[exchanges_core.ExchangeConfig], 
    user_auth: typing.Optional[octobot_flow.entities.UserAuthentication]
) -> octobot_commons.profiles.ProfileData:
    profile_data = octobot_commons.profiles.ProfileData(
        profile_details=octobot_commons.profiles.profile_data.ProfileDetailsData(),
        trading=octobot_commons.profiles.profile_data.TradingData(""),
        exchanges=[
            _create_profile_exchange_data(exchange_config)
            for exchange_config in exchange_configs
        ],
    )
    tentacles_data = octobot_commons.profiles.profile_data.TentaclesData(
        simple_market_making_trading.SimpleMarketMakingTradingMode.get_name(),
        {
            simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: []
        }
    )
    await _apply_market_making_translator(
        profile_data, tentacles_data, exchange_configs, user_auth
    )
    return profile_data


async def _get_market_making_profile_data(
    exchange_configs: list[exchanges_core.ExchangeConfig],
    market_making_config: market_making_configuration_model.MarketMakingConfiguration,
    auth: typing.Optional[octobot_flow.entities.UserAuthentication]
) -> octobot_commons.profiles.ProfileData:
    if not market_making_config:
        raise ValueError(f"{market_making_config} is empty")
    profile_data = octobot_commons.profiles.ProfileData(
        octobot_commons.profiles.profile_data.ProfileDetailsData(),
        [],
        octobot_commons.profiles.profile_data.TradingData("")
    )
    translated_market_making_config = _to_simple_market_making_tentacle_config(
        market_making_config
    )
    tentacles_data = octobot_commons.profiles.profile_data.TentaclesData.from_dict(
        {
            "name": simple_market_making_trading.SimpleMarketMakingTradingMode.get_name(),
            "config": translated_market_making_config,
        }
    )
    await _apply_market_making_translator(
        profile_data, tentacles_data, exchange_configs, auth
    )
    return profile_data


def _to_simple_market_making_tentacle_config(
    market_making_configuration: market_making_configuration_model.MarketMakingConfiguration,
) -> dict:
    # Protocol config uses symbol_configurations/symbol, while the existing
    # SimpleMarketMakingProfileDataAdapter expects pair_settings/trading_pair.
    return {
        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: [
            symbol_configuration.model_dump(
                by_alias=True,
                exclude_none=True,
                mode="json",
            ) for symbol_configuration in market_making_configuration.pair_settings
        ]
    }


async def _apply_market_making_translator(
    profile_data: octobot_commons.profiles.ProfileData, 
    tentacles_data: octobot_commons.profiles.profile_data.TentaclesData, 
    exchange_configs: list[exchanges_core.ExchangeConfig], 
    auth: typing.Optional[octobot_flow.entities.UserAuthentication]
):
    additional_data = {
        community_enums.BotConfigKeys.EXCHANGES.value: [exchange.model_dump() for exchange in exchange_configs]
    }
    translator = octobot_commons.profiles.TentaclesProfileDataTranslator(
        profile_data, []
    )
    if _requires_exchange_auth(exchange_configs):
        for auth_data in translator.auth_data:
            if auth_data.internal_name not in auth.encrypted_keys_by_exchange:
                raise NotImplementedError(f"Exchange auth is not implemented for {auth_data.internal_name}")
        # todo implement if required
        # import tentacles.Meta.Keywords.business_bot_community_library as business_bot_community_library
        # # auth required
        # if not auth or not auth.email or not auth.user_id:
        #     # auth required but not provided, skip auth
        #     missing = [
        #         element
        #         for element, value in {
        #             "auth.email": auth.email,
        #             "auth.user_id": auth.user_id,
        #         }.items()
        #         if not value
        #     ] if auth else f"auth is {auth}"
        #     message = f"All auth.email and auth.user_id are required when exchange auth is required. {exchange_configs=}. Missing: {missing}"
        #     _get_logger().error(message)
        #     raise ValueError(message)
        # else:
        #     async with kw_community.local_community_admin_authenticator(None, user_email=auth.email) as authenticator:
        #         auth.auth_key = await business_bot_community_library.fetch_user_auth_key(
        #             authenticator, auth.user_id, kw_constants.GET_USER_AUTH_SECRET_KEY
        #         )
        #         await translator.translate([tentacles_data], additional_data, authenticator, auth.auth_key)
        #         for auth_data in translator.auth_data:
        #             auth.encrypted_keys_by_exchange[auth_data.internal_name] = auth_data.encrypted
        #     return
    # no auth required
    await translator.translate([tentacles_data], additional_data, None, None)


def _requires_exchange_auth(exchange_configs: list[exchanges_core.ExchangeConfig]) -> bool:
    return simple_market_making_profile_data_adapter.SimpleMarketMakingProfileDataAdapter.requires_exchange_auth(
        [exchange.model_dump() for exchange in exchange_configs]
    )


def get_market_making_traded_pairs_and_config_by_exchange(
    profile_data: octobot_commons.profiles.ProfileData, exchanges: list[str]
) -> dict[str, dict[str, dict]]:
    mm_config = profile_data.get_config_by_tentacle()[
        simple_market_making_trading.SimpleMarketMakingTradingMode.get_name()
    ]
    pair_config_by_pair_by_exchange = {
        exchange: {}
        for exchange in exchanges
    }
    for exchange in exchanges:
        pair_config_by_pair_by_exchange[exchange] = {
            pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR]: pair_config
            for pair_config in mm_config[simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS]
            if (not pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE]) or
               pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE] == exchange
        }
    return {
        exchange: {
            pair: pair_config_by_pair_by_exchange[exchange][pair]
            for pair in profile_data.get_traded_symbols()
            if pair in pair_config_by_pair_by_exchange[exchange]
        }
        for exchange in exchanges
    }


def get_order_book_distribution(pair_config: dict):
    return simple_market_making_trading.SimpleMarketMakingTradingMode.get_order_book_distribution(pair_config)


def get_trading_exchanges(
    profile_data: octobot_commons.profiles.ProfileData,
    mm_exchanges: list[str],
) -> list[str]:
    mm_config = profile_data.get_config_by_tentacle()
    return [
        exchange_name
        for exchange_name in mm_exchanges
        if simple_market_making_trading.SimpleMarketMakingTradingMode.has_trading_exchange_configuration(
            exchange_name, mm_config[simple_market_making_trading.SimpleMarketMakingTradingMode.get_name()]
        )
    ]


def get_aggregated_price_sources_by_exchange(
    profile_data: octobot_commons.profiles.ProfileData,
    mm_exchanges: list[str],
) -> dict[str, list]:
    aggregated_sources_by_exchange = {
        mm_exchange: []
        for mm_exchange in mm_exchanges
    }
    mm_config_by_pair_by_exchange = get_market_making_traded_pairs_and_config_by_exchange(profile_data, mm_exchanges)
    for mm_exchange in mm_exchanges:
        for pair, pair_config in mm_config_by_pair_by_exchange[mm_exchange].items():
            added_local_pair = False
            price_sources_by_exchange = (
                simple_market_making_trading.SimpleMarketMakingTradingMode.get_price_sources_by_exchange(pair_config)
            )
            for exchange, sources in price_sources_by_exchange.items():
                for source in sources:
                    exchange_internal_name = mm_exchange if (
                        exchange == simple_market_making_trading.SimpleMarketMakingTradingMode.LOCAL_EXCHANGE_PRICE
                    ) else exchange
                    if exchange_internal_name not in aggregated_sources_by_exchange:
                        aggregated_sources_by_exchange[exchange_internal_name] = []
                    if source.time_frame is None:
                        source.time_frame = advanced_reference_price_import.DEFAULT_TIME_FRAME
                    if source not in aggregated_sources_by_exchange[exchange_internal_name]:
                        aggregated_sources_by_exchange[exchange_internal_name].append(source)
                    if exchange_internal_name == mm_exchange and source.pair == pair:
                        added_local_pair = True
            if not added_local_pair:
                # ensure local pair is always added in order to fetch required market making data
                local_source = advanced_reference_price_import.AdvancedPriceSource(
                    exchange=simple_market_making_trading.SimpleMarketMakingTradingMode.LOCAL_EXCHANGE_PRICE,
                    pair=pair,
                    time_frame=advanced_reference_price_import.DEFAULT_TIME_FRAME,
                    weight=octobot_trading.constants.ZERO,
                    formula="",
                )
                if local_source not in aggregated_sources_by_exchange[mm_exchange]:
                    aggregated_sources_by_exchange[mm_exchange].append(local_source)
    return aggregated_sources_by_exchange


async def get_reference_price_by_pair(
    mm_config_by_pair_by_exchange: dict,
    mm_data_by_exchange: dict[str, dict[str, models.MarketMakingData]],
    mm_exchange: str,
) -> (dict, dict):
    reference_price_by_pair = {}
    error_by_pair = {}
    if mm_exchange not in mm_config_by_pair_by_exchange:
        return reference_price_by_pair, error_by_pair
    mm_config_by_pair = mm_config_by_pair_by_exchange[mm_exchange]
    for pair, pair_config in mm_config_by_pair.items():
        if not mm_data_by_exchange[mm_exchange].get(pair):
            error_by_pair[pair] = _get_missing_symbol_message(pair, mm_exchange)
            # an error occurred: abort this pair
            continue
        price_sources_by_exchange = (
            simple_market_making_trading.SimpleMarketMakingTradingMode.get_price_sources_by_exchange(pair_config)
        )
        price_by_source = {}
        for exchange, sources in price_sources_by_exchange.items():
            price_by_source[exchange] = {}
            exchange_internal_name = mm_exchange if (
                exchange == simple_market_making_trading.SimpleMarketMakingTradingMode.LOCAL_EXCHANGE_PRICE
            ) else exchange
            candle_manager_by_time_frame_by_symbol = _get_candle_manager_by_time_frame_by_symbol(
                mm_data_by_exchange[exchange_internal_name]
            )
            price_by_symbol = {
                **{
                    mm_data.pair_alias: mm_data.price 
                    for mm_data in mm_data_by_exchange[exchange_internal_name].values()
                    if mm_data.pair_alias
                },
                **{
                    mm_data.pair: mm_data.price
                    for mm_data in mm_data_by_exchange[exchange_internal_name].values()
                }
            }
            for source in sources:
                try:
                    if source.formula:
                        await source.initialize_if_required(
                            None, candle_manager_by_time_frame_by_symbol, price_by_symbol
                        )
                    price_by_source[exchange][source.pair] = mm_data_by_exchange[exchange_internal_name][source.pair].price
                except octobot_commons.errors.DSLInterpreterError as err:
                    error_by_pair[pair] = f"Invalid {source.pair} reference price formula: {err}"
                except KeyError:
                    error_by_pair[pair] = _get_missing_symbol_message(source.pair, exchange_internal_name)
                    break
        if pair in error_by_pair:
            # an error occurred: abort this pair
            continue
        try:
            reference_price_by_pair[pair] = await advanced_reference_price_import.compute_reference_price(
                price_by_source, price_sources_by_exchange
            )
        except (NotImplementedError, TypeError, ValueError) as err:
            error_by_pair[pair] = f"{err}"
            continue
        if not reference_price_by_pair[pair]:
            error_by_pair[pair] = (
                f"{pair} reference price on {mm_exchange} can't be computed from the following "
                f"price sources: {price_by_source}"
            )
    return reference_price_by_pair, error_by_pair


def _get_candle_manager_by_time_frame_by_symbol(
    mm_data_by_pair: dict[str, models.MarketMakingData]
) -> dict[str, dict[str, octobot_trading.exchange_data.CandlesManager]]:
    candle_manager_by_time_frame_by_symbol = {}
    for symbol, mm_data in mm_data_by_pair.items():
        for market_detail in mm_data.market_details:
            if market_detail.time_frame not in candle_manager_by_time_frame_by_symbol:
                candle_manager_by_time_frame_by_symbol[market_detail.time_frame] = {}
            candles_manager = octobot_trading.exchange_data.CandlesManager(
                max_candles_count=len(market_detail.close)
            )
            candles_manager.replace_all_candles(market_detail.get_formatted_candles())
            candle_manager_by_time_frame_by_symbol[market_detail.time_frame][symbol] = candles_manager

    return candle_manager_by_time_frame_by_symbol


def _adapt_volume_if_necessary(mm_data: models.MarketMakingData, reference_price: decimal.Decimal):
    missing_base = not mm_data.base_volume or mm_data.base_volume.is_nan()
    missing_quote = not mm_data.quote_volume or mm_data.quote_volume.is_nan()
    default_min_base_vol, default_min_quote_vol = (
        simple_market_making_trading.SimpleMarketMakingTradingMode.get_default_min_base_and_quote_volume(
            mm_data.pair, reference_price, mm_data.quote_volume
        )
    )
    if missing_base or missing_quote:
        if missing_base:
            mm_data.base_volume = default_min_base_vol
        if missing_quote:
            mm_data.quote_volume = default_min_quote_vol
    if mm_data.base_volume < default_min_base_vol:
        mm_data.base_volume = default_min_base_vol
    if mm_data.quote_volume < default_min_quote_vol:
        mm_data.quote_volume = default_min_quote_vol


async def _get_price_and_predicted_order_book(
    profile_data: octobot_commons.profiles.ProfileData,
    mm_data_by_exchange: dict[str, dict[str, models.MarketMakingData]],
    mm_exchange: str,
) -> dict:
    mm_config_by_pair_by_exchange = get_market_making_traded_pairs_and_config_by_exchange(
        profile_data, [mm_exchange]
    )
    reference_price_by_pair, error_by_pair = await get_reference_price_by_pair(
        mm_config_by_pair_by_exchange, mm_data_by_exchange, mm_exchange
    )
    books_by_symbol = {}
    for pair, reference_price in reference_price_by_pair.items():
        if not reference_price:
            continue
        mm_data = mm_data_by_exchange[mm_exchange].get(pair)
        _adapt_volume_if_necessary(mm_data, reference_price)
        pair_config = mm_config_by_pair_by_exchange[mm_exchange].get(pair)
        try:
            distribution = get_order_book_distribution(pair_config).compute_distribution(
                reference_price,
                mm_data.base_volume,
                mm_data.quote_volume,
                mm_data.market_status,
            )
            books_by_symbol[pair] = {
                constants.PRICE_KEY: reference_price,
                constants.BIDS_KEY: _book_order_data_to_dict(distribution.bids),
                constants.ASKS_KEY: _book_order_data_to_dict(distribution.asks),
                constants.VOLUME_KEY: _get_ideal_volume_by_symbol(
                    pair, distribution, reference_price, mm_data, mm_exchange
                )
            }
        except ValueError as err:
            error_by_pair[pair] = str(err)
    for pair, error in error_by_pair.items():
        # register errors
        books_by_symbol[pair] = {
            constants.ERROR_KEY: error,
        }
    return books_by_symbol


def _book_order_data_to_dict(order_data: list) -> list[dict]:
    return [
        {
            constants.PRICE_KEY: data.price,
            constants.AMOUNT_KEY: data.amount,
            constants.TOTAL_KEY: data.price * data.amount,  # todo update when using futures
        }
        for data in order_data
    ]



def _get_missing_symbol_message(symbol: str, exchange: str) -> str:
    return (
        f"{symbol} not found in {exchange} all market data (price ticker empty or not found). "
        f"{symbol} market is likely missing or disabled on {exchange}"
    )


def _format_format_market_making_volume(volume: typing.Union[dict, None], error: typing.Union[str, None]):
    return {
        constants.VOLUME_KEY: volume,
        constants.ERROR_KEY: error,
    }


def _create_market_data(
    exchange_internal_name: str, 
    symbol: str,
    pair_alias: typing.Optional[str],
    ticker: typing.Optional[dict], 
    market_statuses: dict, 
    market_details: list[octobot_trading.exchanges.MarketDetails]
) -> models.MarketMakingData:
    if ticker is None:
        price = base_volume = quote_volume = decimal.Decimal("nan")
    else:
        price = decimal.Decimal(str(ticker[octobot_trading.enums.ExchangeConstantsTickersColumns.CLOSE.value]))
        try:
            base_volume, quote_volume = octobot_trading.api.get_daily_base_and_quote_volume_from_ticker(
                ticker, reference_price=price
            )
        except ValueError:
            base_volume = quote_volume = decimal.Decimal("nan")
    return models.MarketMakingData(
        exchange_internal_name,
        symbol,
        pair_alias,
        price,
        base_volume,
        quote_volume,
        market_statuses.get(symbol, None),
        market_details,
    )


def format_market_making_volume_by_symbol(volume_by_symbol, error_by_symbol) -> dict:
    result_by_symbol = {
        symbol: _format_format_market_making_volume(volume, None)
        for symbol, volume in volume_by_symbol.items()
    }
    for symbol, error in error_by_symbol.items():
        if result := result_by_symbol.get(symbol, None):
            result[constants.ERROR_KEY] = error
        else:
            result_by_symbol[symbol] = _format_format_market_making_volume(None, error)
    return result_by_symbol


async def get_minimal_volume_by_symbol(
    profile_data: octobot_commons.profiles.ProfileData,
    mm_exchange: str,
    mm_data_by_exchange: dict[str, dict[str, models.MarketMakingData]]
) -> (dict[str, dict], dict[str, str]):
    mm_config_by_pair_by_exchange = get_market_making_traded_pairs_and_config_by_exchange(
        profile_data, [mm_exchange]
    )
    reference_price_by_pair, error_by_pair = await get_reference_price_by_pair(
        mm_config_by_pair_by_exchange, mm_data_by_exchange, mm_exchange
    )
    volumes_by_symbol = {}
    for pair, reference_price in reference_price_by_pair.items():
        if not reference_price:
            continue
        mm_data = mm_data_by_exchange[mm_exchange].get(pair)
        _adapt_volume_if_necessary(mm_data, reference_price)
        pair_config = mm_config_by_pair_by_exchange[mm_exchange].get(pair)
        distribution = get_order_book_distribution(pair_config)
        try:
            volumes_by_symbol[pair] = _get_ideal_volume_by_symbol(
                pair, distribution, reference_price, mm_data, mm_exchange
            )
        except ValueError as err:
            error_by_pair[pair] = str(err)
    return volumes_by_symbol, error_by_pair


def _get_ideal_volume_by_symbol(
    pair, distribution, reference_price, mm_data, mm_exchange
):
    base, quote = commons_symbols.parse_symbol(pair).base_and_quote()
    try:
        return {
            base: distribution.get_ideal_total_volume(
                octobot_trading.enums.TradeOrderSide.SELL,
                reference_price,
                mm_data.base_volume,
                mm_data.quote_volume,
            ),
            quote: distribution.get_ideal_total_volume(
                octobot_trading.enums.TradeOrderSide.BUY,
                reference_price,
                mm_data.base_volume,
                mm_data.quote_volume,
            )
        }
    except ValueError as err:
        raise ValueError(
            f"{pair} minimum volume on {mm_exchange} can't be computed "
            f"with the current configuration: {err}"
        ) from err


def _ensure_no_missing_book_data(sorted_orders: list[dict], price_threshold: float, are_bids: bool):
    # ensure enough orders are fetched
    if are_bids:
        # lowest bid price is <= price_threshold
        if not sorted_orders[-1][0] <= price_threshold:
            raise octobot_trading.errors.MissingPriceDataError
    else:
        # highest ask price is >= price_threshold
        if not sorted_orders[-1][0] >= price_threshold:
            raise octobot_trading.errors.MissingPriceDataError


def _get_order_book_orders_depth(
    description: str, sorted_orders: list[dict], price_threshold: float, are_bids: bool, check_missing_data: bool
) -> decimal.Decimal:
    try:
        _ensure_no_missing_book_data(sorted_orders, price_threshold, are_bids)
    except octobot_trading.errors.MissingPriceDataError:
        if check_missing_data:
            raise
        side = 'buy' if are_bids else 'sell'
        _get_logger().warning(
            f"Not enough {side} orders in {description} book to properly "
            f"compute order book depth: {len(sorted_orders)} {side} orders have been fetched. Computing score anyway."
        )
    return decimal.Decimal(str(sum(
        # unit: quote if bid, base if ask
        decimal.Decimal(str(order[1])) * (decimal.Decimal(str(order[0])) if are_bids else octobot_trading.constants.ONE)
        for order in sorted_orders
        if (order[0] >= price_threshold if are_bids else order[0] <= price_threshold)
    )))


def _get_order_book_depth_score(order_book_depth_ratio: decimal.Decimal) -> decimal.Decimal:
    # - High depth: Cumulative volume within 1% of mid-price covers > 2% of daily trading volume
    # - Moderate depth: Cumulative volume within 1% of mid-price covers 0.5% - 2% of daily trading volume
    # - Low depth: Cumulative volume within 1% of mid-price covers < 0.5% of daily trading volume
    for depth_score_threshold in constants.DEPTH_SCORE_THRESHOLDS:
        threshold_ratios, values = depth_score_threshold[0], depth_score_threshold[1]
        if threshold_ratios[0] <= order_book_depth_ratio <= threshold_ratios[1]:
            return values[0] + (
                order_book_depth_ratio / threshold_ratios[1] * (values[1] - values[0])
            )
    return octobot_trading.constants.ZERO


def _get_spread_score(spread_ratio: decimal.Decimal) -> decimal.Decimal:
    # - Tight spread (high liquidity) (small) :  0.01% - 0.1% of the asset price
    # - Moderate spread: 0.1% - 0.5% of the asset price
    # - Wide spread (low liquidity) (large) : > 0.5% of the asset price
    for spread_threshold in constants.SPREAD_SCORE_THRESHOLDS:
        threshold_ratios, values = spread_threshold[0], spread_threshold[1]
        if threshold_ratios[0] <= spread_ratio <= threshold_ratios[1]:
            return values[0] + (
                spread_ratio / threshold_ratios[1] * (values[1] - values[0])
            )
    return octobot_trading.constants.ZERO


def _get_bidask_score(
    description: str, mid_price: float, ticker: dict, sorted_orders: list, are_bids: bool, check_missing_data: bool
):
    depth = _get_order_book_orders_depth(
        description, sorted_orders, mid_price * (1 + (constants.DEPTH_SCORE_MID_PRICE_THRESHOLD * (-1 if are_bids else 1))),
        are_bids, check_missing_data
    )
    try:
        base_volume, quote_volume = octobot_trading.api.get_daily_base_and_quote_volume_from_ticker(ticker)
        depth_ratio = depth / (quote_volume if are_bids else base_volume)
    except (ValueError, decimal.DecimalException):
        # missing quote and base volume: can't compute score
        depth_ratio = octobot_trading.constants.ZERO
    return _get_order_book_depth_score(depth_ratio), depth_ratio

def get_missing_data_liquidity_scores(exchange_id: str, symbols: list[str]) -> list[models.LiquidityScore]:
    current_time = time.time()
    timestamp = current_time - (
        current_time % (
            # allow max 1 update every day (as there is no data anyway)
            octobot_commons.enums.TimeFramesMinutes[octobot_commons.enums.TimeFrames.ONE_DAY]
            * octobot_commons.constants.MINUTE_TO_SECONDS
        )
    )
    return [
        models.LiquidityScore(
            timestamp=timestamp,
            exchange_id=exchange_id,
            symbol=symbol,
            score=0,
            bid_ask_spread=None ,
            bids_ob_depth=None,
            asks_ob_depth=None,
        )
        for symbol in symbols
    ]

def get_liquidity_score(
    exchange_id: str, exchange: str, symbol: str, ticker: dict, order_book: dict, check_missing_data: bool
) -> models.LiquidityScore:
    higher_to_lower_bids = sorted(
        order_book[octobot_trading.enums.ExchangeConstantsOrderBookInfoColumns.TIMESTAMP.BIDS.value],
        key=lambda x: x[0],
        reverse=True
    )
    lower_to_higher_asks = sorted(
        order_book[octobot_trading.enums.ExchangeConstantsOrderBookInfoColumns.TIMESTAMP.ASKS.value],
        key=lambda x: x[0]
    )
    bids_depth_ratio = None
    asks_depth_ratio = None
    bid_ask_spread_ratio = None
    if lower_to_higher_asks == higher_to_lower_bids == []:
        # no order at all
        score = octobot_trading.constants.ZERO
    else:
        spread_score = bids_depth_score = asks_depth_score = octobot_trading.constants.ZERO
        if lower_to_higher_asks and higher_to_lower_bids:
            mid_price = (lower_to_higher_asks[0][0] + higher_to_lower_bids[0][0]) / 2
        else:
            # default to ticker last price
            mid_price = ticker[octobot_trading.enums.ExchangeConstantsTickersColumns.CLOSE.value]
        description = f"[{exchange}] {symbol}"
        if mid_price is None:
            _get_logger().warning(
                f"No middle bid-ask price for {description}: can't compute liquidity score"
            )
        else:
            if higher_to_lower_bids:
                bids_depth_score, bids_depth_ratio = _get_bidask_score(
                    description, mid_price, ticker, higher_to_lower_bids, True, check_missing_data
                )
            else:
                _get_logger().info(f"No open buy order in book for {description}")
            if lower_to_higher_asks:
                asks_depth_score, asks_depth_ratio = _get_bidask_score(
                    description, mid_price, ticker, lower_to_higher_asks, False, check_missing_data
                )
            else:
                _get_logger().info(f"No open sell order in book for {description}")
            if lower_to_higher_asks and higher_to_lower_bids:
                bid_ask_spread = lower_to_higher_asks[0][0] - higher_to_lower_bids[0][0]
                bid_ask_spread_ratio = decimal.Decimal(str(bid_ask_spread)) / decimal.Decimal(str(mid_price))
                spread_score = _get_spread_score(bid_ask_spread_ratio)
        score = (
            constants.LIQUIDITY_SCORE_DEPTH_SCORE_PART * (bids_depth_score + asks_depth_score) / decimal.Decimal(2)
            + constants.LIQUIDITY_SCORE_SPREAD_SCORE_PART * spread_score
        )
    return models.LiquidityScore(
        timestamp=order_book[octobot_trading.enums.ExchangeConstantsOrderBookInfoColumns.TIMESTAMP.value],
        exchange_id=exchange_id,
        symbol=symbol,
        score=float(score),
        bid_ask_spread=None if bid_ask_spread_ratio is None else float(bid_ask_spread_ratio),
        bids_ob_depth=None if bids_depth_ratio is None else float(bids_depth_ratio),
        asks_ob_depth=None if asks_depth_ratio is None else float(asks_depth_ratio),
    )


async def _fetch_order_books(exchange_manager: octobot_trading.exchanges.ExchangeManager, symbols: list[str], limit: int):
    # try using fetch_order_books directly otherwise sur fetch_order_book for each symbol
    try:
        _get_logger().info(f"Fetching {symbols} order books [{exchange_manager.exchange_name}]")
        order_book_by_symbol = await exchange_manager.exchange.get_order_books(symbols=symbols, limit=limit)
        _get_logger().info(
            f"Fetched {len(order_book_by_symbol)} order books [{exchange_manager.exchange_name}]"
        )
        for symbol, book in order_book_by_symbol.items():
            if symbol in symbols:
                yield symbol, book
    except octobot_trading.errors.NotSupported:
        _get_logger().info(
            f"Fetching [{exchange_manager.exchange_name}] multiple order books at once is not supported, "
            f"fetching them one by one."
        )
        for index, symbol in enumerate(symbols):
            try:
                order_book = await _fetch_order_book(exchange_manager, symbol, limit, False)
                _get_logger().info(
                    f"Fetched {index + 1}/{len(symbols)} {symbol} order book [{exchange_manager.exchange_name}] "
                    f"[{len(order_book[octobot_trading.enums.ExchangeConstantsOrderBookInfoColumns.BIDS.value])} bids, "
                    f"{len(order_book[octobot_trading.enums.ExchangeConstantsOrderBookInfoColumns.ASKS.value])} asks]"
                )
                yield symbol, order_book
            except octobot_trading.errors.FailedRequest as err:
                _get_logger().warning(
                    f"Skipped [{exchange_manager.exchange_name}] {symbol} "
                    f"order books update: ({err.__class__.__name__}: {err})."
                )


def get_symbols_to_fetch(
    policy: models.OrderBookFetchPolicy,
    available_symbols: list[str],
    symbols: typing.Optional[list[str]],
) -> list[str]:
    if policy is models.OrderBookFetchPolicy.GIVEN_SYMBOLS:
        if not symbols:
            raise ValueError("Input symbols are required when using this policy")
        return symbols
    if policy is models.OrderBookFetchPolicy.ALL_SYMBOLS:
        return available_symbols
    raise ValueError(f"Policy {policy} is not supported")

async def _fetch_tickers(
    exchange_manager,
    tickers: dict,
    symbols: list[str],
) -> tuple[dict, octobot_trading.exchange_data.TickerUpdater]:
    ticker_updater = typing.cast(
        octobot_trading.exchange_data.TickerUpdater,
        octobot_trading.api.get_channel_updater(
            exchange_manager, octobot_trading.constants.TICKER_CHANNEL
        )
    )
    if not tickers:
        try:
            tickers = await ticker_updater.fetch_all_tickers(symbols)
        except octobot_trading.errors.NotSupported as err:
            _get_logger().info(f"Fetching tickers for {symbols} is not supported: {err}")
            tickers = {}
    return tickers, ticker_updater


async def _fetch_order_book(exchange_manager: octobot_trading.exchanges.ExchangeManager, symbol: str, limit: int, log: bool) -> dict:
    if log:
        _get_logger().info(f"Fetching {symbol} order book [{exchange_manager.exchange_name}] {limit=}")
    order_book = await exchange_manager.exchange.get_order_book(symbol, limit=limit)
    if not order_book:
        raise ValueError(f"No order book found for {symbol} [{exchange_manager.exchange_name}]")
    if log:
        _get_logger().info(
            f"Fetched {symbol} order book [{exchange_manager.exchange_name}] {limit=} "
            f"[{len(order_book[octobot_trading.enums.ExchangeConstantsOrderBookInfoColumns.BIDS.value])} bids, "
            f"{len(order_book[octobot_trading.enums.ExchangeConstantsOrderBookInfoColumns.ASKS.value])} asks]"
        )
    return order_book


def _get_logger() -> octobot_commons.logging.BotLogger:
    return octobot_commons.logging.get_logger("market_making_api.core")
