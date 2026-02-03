#  Drakkar-Software OctoBot-Tentacles
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
import json
import sortedcontainers

import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.exchange_data as trading_exchange_data
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.personal_data.portfolios.portfolio_util as portfolio_util
import octobot_trading.api as trading_api
import octobot_backtesting.api as backtesting_api
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.constants
import octobot_commons.databases as databases
import octobot_commons.enums as commons_enums
import octobot_commons.errors as commons_errors
import octobot_commons.time_frame_manager as time_frame_manager
import octobot_commons.logging


def get_logger():
    return octobot_commons.logging.get_logger("BacktestingRunData")


async def get_candles(candles_sources, exchange, symbol, time_frame, metadata):
    return await backtesting_api.get_all_ohlcvs(candles_sources[0][commons_enums.DBRows.VALUE.value],
                                                exchange,
                                                symbol,
                                                commons_enums.TimeFrames(time_frame),
                                                inferior_timestamp=metadata[commons_enums.DBRows.START_TIME.value],
                                                superior_timestamp=metadata[commons_enums.DBRows.END_TIME.value])


async def get_trades(meta_database, metadata, symbol):
    account_type = trading_api.get_account_type_from_run_metadata(metadata)
    return await meta_database.get_trades_db(account_type).select(
        commons_enums.DBTables.TRADES.value,
        (await meta_database.get_trades_db(account_type).search()).symbol == symbol
    )


async def get_metadata(meta_database):
    return (await meta_database.get_run_db().all(commons_enums.DBTables.METADATA.value))[0]


async def get_transactions(meta_database, transaction_type=None, transaction_types=None):
    account_type = trading_api.get_account_type_from_run_metadata(await get_metadata(meta_database))
    if transaction_type is not None:
        query = (await meta_database.get_transactions_db(account_type).search()).type == transaction_type
    elif transaction_types is not None:
        query = (await meta_database.get_transactions_db(account_type).search()).type.one_of(transaction_types)
    else:
        return await meta_database.get_transactions_db(account_type).all(commons_enums.DBTables.TRANSACTIONS.value)
    return await meta_database.get_transactions_db(account_type).select(commons_enums.DBTables.TRANSACTIONS.value,
                                                                        query)


async def get_starting_portfolio(meta_database) -> dict:
    portfolio = (await meta_database.get_run_db().all(commons_enums.DBTables.METADATA.value))[0][
        commons_enums.BacktestingMetadata.START_PORTFOLIO.value]
    return json.loads(portfolio.replace("'", '"'))


async def load_historical_values(meta_database, exchange, with_candles=True,
                                 with_trades=True, with_portfolio=True, time_frame=None):
    price_data = {}
    trades_data = {}
    moving_portfolio_data = {}
    trading_type = "spot"
    metadata = {}
    run_global_metadata = {}
    try:
        starting_portfolio = await get_starting_portfolio(meta_database)
        metadata = await get_metadata(meta_database)
        run_global_metadata = await meta_database.get_backtesting_metadata_from_run()

        exchange = exchange or meta_database.run_dbs_identifier.context.exchange_name \
            or metadata[commons_enums.DBRows.EXCHANGES.value][0]  # TODO handle multi exchanges
        ref_market = metadata[commons_enums.DBRows.REFERENCE_MARKET.value]
        trading_type = metadata[commons_enums.DBRows.TRADING_TYPE.value]
        contracts = metadata[commons_enums.DBRows.FUTURE_CONTRACTS.value][exchange] if trading_type == "future" else {}
        # init data
        for pair in run_global_metadata[commons_enums.DBRows.SYMBOLS.value]:
            symbol = symbol_util.parse_symbol(pair).base
            is_inverse_contract = trading_type == "future" and trading_api.is_inverse_future_contract(
                trading_enums.FutureContractType(contracts[pair]["contract_type"])
            )
            if symbol != ref_market or is_inverse_contract:
                candles_sources = await meta_database.get_symbol_db(exchange, pair).all(
                    commons_enums.DBTables.CANDLES_SOURCE.value
                )
                if time_frame is None:
                    time_frames = [source[commons_enums.DBRows.TIME_FRAME.value] for source in candles_sources]
                    time_frame = time_frame_manager.find_min_time_frame(time_frames) if time_frames else time_frame
                if with_candles and pair not in price_data:
                    # convert candles timestamp in millis
                    raw_candles = await get_candles(candles_sources, exchange, pair, time_frame, metadata)
                    for candle in raw_candles:
                        candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value] = \
                            candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value] * 1000
                    price_data[pair] = raw_candles
                if with_trades and pair not in trades_data:
                    trades_data[pair] = await get_trades(meta_database, metadata, pair)
            if with_portfolio:
                try:
                    moving_portfolio_data[symbol] = starting_portfolio[symbol][
                        octobot_commons.constants.PORTFOLIO_TOTAL]
                except KeyError:
                    moving_portfolio_data[symbol] = 0
                try:
                    moving_portfolio_data[ref_market] = starting_portfolio[ref_market][
                        octobot_commons.constants.PORTFOLIO_TOTAL]
                except KeyError:
                    moving_portfolio_data[ref_market] = 0
    except IndexError:
        pass
    return price_data, trades_data, moving_portfolio_data, trading_type, metadata, run_global_metadata


async def backtesting_data(meta_database, data_label):
    metadata_from_run = await meta_database.get_backtesting_metadata_from_run()
    for key, value in metadata_from_run.items():
        if key == data_label:
            return value
    account_type = trading_api.get_account_type_from_run_metadata(metadata_from_run)
    for reader in meta_database.all_basic_run_db(account_type):
        for table in await reader.tables():
            if table == data_label:
                return await reader.all(table)
            for row in await reader.all(table):
                for key, value in row.items():
                    if key == data_label:
                        return value
    return None


async def _get_grouped_funding_fees(meta_database, group_key):
    funding_fees_history = await get_transactions(meta_database,
                                                  transaction_type=trading_enums.TransactionType.FUNDING_FEE.value)
    funding_fees_history = sorted(funding_fees_history, key=lambda f: f[commons_enums.PlotAttributes.X.value])
    funding_fees_history_by_key = {}
    for funding_fee in funding_fees_history:
        try:
            funding_fees_history_by_key[funding_fee[group_key]].append(funding_fee)
        except KeyError:
            funding_fees_history_by_key[funding_fee[group_key]] = [funding_fee]
    return funding_fees_history_by_key


async def plot_historical_funding_fees(meta_database, plotted_element, own_yaxis=True):
    funding_fees_history_by_currency = await _get_grouped_funding_fees(
        meta_database,
        trading_enums.FeePropertyColumns.CURRENCY.value
    )
    for currency, fees in funding_fees_history_by_currency.items():
        cumulative_fees = []
        previous_fee = 0
        for fee in fees:
            cumulated_fee = fee["quantity"] + previous_fee
            cumulative_fees.append(cumulated_fee)
            previous_fee = cumulated_fee
        plotted_element.plot(
            mode="scatter",
            x=[fee[commons_enums.PlotAttributes.X.value] for fee in fees],
            y=cumulative_fees,
            title=f"{currency} paid funding fees",
            own_yaxis=own_yaxis,
            line_shape="hv")


def _position_factory(symbol, contract_data):
    # TODO: historical unrealized pnl, maybe find a better solution that this
    import mock
    class _TraderMock:
        def __init__(self):
            self.exchange_manager = mock.Mock()
            self.simulate = True

    contract = trading_exchange_data.FutureContract(
        symbol,
        trading_enums.MarginType(contract_data["margin_type"]),
        trading_enums.FutureContractType(contract_data["contract_type"])
    )
    return trading_personal_data.create_position_from_type(_TraderMock(), contract)


def _evaluate_portfolio(portfolio, price_data, use_start_value):
    handled_currencies = []
    value = 0

    vals = {}
    for pair, candles in price_data.items():
        candle = candles[0 if use_start_value else len(candles) - 1]
        symbol, ref_market = symbol_util.parse_symbol(pair).base_and_quote()
        if symbol not in handled_currencies:
            value += portfolio.get(symbol, {}).get(octobot_commons.constants.PORTFOLIO_TOTAL, 0) * candle[
                commons_enums.PriceIndexes.IND_PRICE_OPEN.value
            ]
            vals[symbol] = candle[
                commons_enums.PriceIndexes.IND_PRICE_OPEN.value
            ]
            handled_currencies.append(symbol)
        if ref_market not in handled_currencies:
            value += portfolio.get(ref_market, {}).get(octobot_commons.constants.PORTFOLIO_TOTAL, 0)
            handled_currencies.append(ref_market)
    return value


async def get_portfolio_values(meta_database, exchange=None, historical_values=None):
    price_data, trades_data, moving_portfolio_data, trading_type, metadata, _ = \
        historical_values or await load_historical_values(meta_database, exchange, with_portfolio=False, with_trades=False)
    starting_portfolio = json.loads(metadata[commons_enums.BacktestingMetadata.START_PORTFOLIO.value].replace("'", '"'))
    ending_portfolio = json.loads(metadata[commons_enums.BacktestingMetadata.END_PORTFOLIO.value].replace("'", '"'))
    return _evaluate_portfolio(
        starting_portfolio,
        price_data,
        True,
    ), _evaluate_portfolio(
        ending_portfolio,
        price_data,
        False,
    )


async def plot_historical_portfolio_value(
    meta_database, plotted_element, exchange=None, own_yaxis=False, historical_values=None
):
    price_data, trades_data, moving_portfolio_data, trading_type, metadata, _ = \
        historical_values or await load_historical_values(meta_database, exchange)
    price_data_by_time = {}
    for symbol, candles in price_data.items():
        price_data_by_time[symbol] = {
            candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value]: candle
            for candle in candles
        }
    if trading_type == "future":
        # TODO: historical unrealized pnl
        pass
    for pair in trades_data:
        trades_data[pair] = sorted(trades_data[pair], key=lambda tr: tr[commons_enums.PlotAttributes.X.value])
    funding_fees_history_by_pair = await _get_grouped_funding_fees(meta_database,
                                                                   commons_enums.DBRows.SYMBOL.value)
    value_data = sortedcontainers.SortedDict()
    pairs = list(trades_data)
    if pairs:
        pair = pairs[0]
        candles = price_data_by_time[pair]
        value_data = sortedcontainers.SortedDict({
            t: 0
            for t in candles
        })
        trade_index_by_pair = {p: 0 for p in pairs}
        funding_fees_index_by_pair = {p: 0 for p in pairs}
        # TODO multi exchanges
        exchange_name = metadata[commons_enums.DBRows.EXCHANGES.value][0]
        # TODO hedge mode with multi position by pair
        # if metadata[commons_enums.DBRows.FUTURE_CONTRACTS.value] and \
        #         exchange_name in metadata[commons_enums.DBRows.FUTURE_CONTRACTS.value]:
        #     positions_by_pair = {
        #         pair: _position_factory(pair,
        #                                 metadata[commons_enums.DBRows.FUTURE_CONTRACTS.value][exchange_name][pair])
        #         for pair in pairs
        #     }
        # else:
        #     positions_by_pair = {}
        # TODO update position instead of portfolio when filled orders and apply position unrealized pnl to portfolio
        for candle_time, ref_candle in candles.items():
            current_candles = {}
            for pair in pairs:
                if candle_time not in price_data_by_time[pair]:
                    # no price data for this time in this pair
                    continue
                other_candle = price_data_by_time[pair][candle_time]
                current_candles[pair] = other_candle
                symbol, ref_market = symbol_util.parse_symbol(pair).base_and_quote()
                moving_portfolio_data[ref_market] = moving_portfolio_data.get(ref_market, 0)
                moving_portfolio_data[symbol] = moving_portfolio_data.get(symbol, 0)
                # part 1: compute portfolio total value after trade update when any
                # 1.1: trades
                # start iteration where it last stopped to reduce complexity
                for trade_index, trade in enumerate(trades_data[pair][trade_index_by_pair[pair]:]):
                    # handle trades that are both older and at the current candle starting from the last trade index
                    # (older trades to handle the ones that might be from candles we dont have data on)
                    if trade[commons_enums.PlotAttributes.X.value] <= candle_time:
                        if trade[commons_enums.PlotAttributes.SIDE.value] == trading_enums.TradeOrderSide.SELL.value:
                            moving_portfolio_data[symbol] -= trade[commons_enums.PlotAttributes.VOLUME.value]
                            moving_portfolio_data[ref_market] += trade[commons_enums.PlotAttributes.VOLUME.value] * \
                                                                 trade[commons_enums.PlotAttributes.Y.value]
                        else:
                            moving_portfolio_data[symbol] += trade[commons_enums.PlotAttributes.VOLUME.value]
                            moving_portfolio_data[ref_market] -= trade[commons_enums.PlotAttributes.VOLUME.value] * \
                                                                 trade[commons_enums.PlotAttributes.Y.value]
                        moving_portfolio_data[trade[commons_enums.DBRows.FEES_CURRENCY.value]] -= \
                            trade[commons_enums.DBRows.FEES_AMOUNT.value]

                        # last trade case: as there is not trade afterwards, the next condition would never be filled,
                        # force trade_index_by_pair[pair] increment
                        if all(it_trade[commons_enums.PlotAttributes.X.value] ==
                               trade[commons_enums.PlotAttributes.X.value]
                               for it_trade in trades_data[pair][trade_index_by_pair[pair]:]):
                            trade_index_by_pair[pair] += 1
                            break

                    if trade[commons_enums.PlotAttributes.X.value] > \
                            ref_candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value]:
                        # no need to continue iterating, save current index for new candle
                        trade_index_by_pair[pair] += trade_index
                        break
                # 1.2: funding fees
                # start iteration where it last stopped to reduce complexity
                for funding_fee_index, funding_fee \
                        in enumerate(funding_fees_history_by_pair.get(pair, [])[funding_fees_index_by_pair[pair]:]):
                    if funding_fee[commons_enums.PlotAttributes.X.value] == candle_time:
                        moving_portfolio_data[funding_fee[trading_enums.FeePropertyColumns.CURRENCY.value]] -= \
                            funding_fee["quantity"]
                    if funding_fee[commons_enums.PlotAttributes.X.value] > candle_time:
                        # no need to continue iterating, save current index for new candle
                        funding_fees_index_by_pair[pair] = funding_fee_index  # TODO
                        break
            # part 2: now that portfolio is up-to-date, compute portfolio total value
            handled_currencies = []
            for pair, other_candle in current_candles.items():
                symbol, ref_market = symbol_util.parse_symbol(pair).base_and_quote()
                if symbol not in handled_currencies:
                    value_data[candle_time] = \
                        value_data[candle_time] + \
                        moving_portfolio_data[symbol] * other_candle[
                            commons_enums.PriceIndexes.IND_PRICE_OPEN.value
                        ]
                    handled_currencies.append(symbol)
                if ref_market not in handled_currencies:
                    value_data[candle_time] = value_data[candle_time] + moving_portfolio_data[ref_market]
                    handled_currencies.append(ref_market)
    plotted_element.plot(
        mode="scatter",
        x=list(value_data.keys()),
        y=list(value_data.values()),
        title="Portfolio value",
        own_yaxis=own_yaxis
    )


def _read_pnl_from_trades(x_data, pnl_data, cumulative_pnl_data, trades_history, x_as_trade_count):
    buy_order_volume_by_price_by_currency = {
        symbol_util.parse_symbol(symbol).base: {}
        for symbol in trades_history.keys()
    }
    all_trades = []
    buy_fees = 0
    sell_fees = 0
    for trades in trades_history.values():
        all_trades += trades
    for trade in sorted(all_trades, key=lambda x: x[commons_enums.PlotAttributes.X.value]):
        currency, ref_market = symbol_util.parse_symbol(trade[commons_enums.DBRows.SYMBOL.value]).base_and_quote()
        trade_volume = trade[commons_enums.PlotAttributes.VOLUME.value]
        buy_order_volume_by_price = buy_order_volume_by_price_by_currency[currency]
        if trade[commons_enums.PlotAttributes.SIDE.value] == trading_enums.TradeOrderSide.BUY.value:
            fees = trade[commons_enums.DBRows.FEES_AMOUNT.value]
            fees_multiplier = 1 if trade[commons_enums.DBRows.FEES_CURRENCY.value] == currency \
                else 1 / trade[commons_enums.PlotAttributes.Y.value]
            paid_fees = fees * fees_multiplier
            buy_fees += paid_fees * trade[commons_enums.PlotAttributes.Y.value]
            buy_cost = trade_volume * trade[commons_enums.PlotAttributes.Y.value]
            if trade[commons_enums.PlotAttributes.Y.value] in buy_order_volume_by_price:
                buy_order_volume_by_price[buy_cost / (trade_volume - paid_fees)] += trade_volume - paid_fees
            else:
                buy_order_volume_by_price[buy_cost / (trade_volume - paid_fees)] = trade_volume - paid_fees
        elif trade[commons_enums.PlotAttributes.SIDE.value] == trading_enums.TradeOrderSide.SELL.value:
            remaining_sell_volume = trade_volume
            volume_by_bought_prices = {}
            for order_price in list(buy_order_volume_by_price.keys()):
                if buy_order_volume_by_price[order_price] > remaining_sell_volume:
                    buy_order_volume_by_price[order_price] -= remaining_sell_volume
                    volume_by_bought_prices[order_price] = remaining_sell_volume
                    remaining_sell_volume = 0
                elif buy_order_volume_by_price[order_price] == remaining_sell_volume:
                    buy_order_volume_by_price.pop(order_price)
                    volume_by_bought_prices[order_price] = remaining_sell_volume
                    remaining_sell_volume = 0
                else:
                    # buy_order_volume_by_price[order_price] < remaining_sell_volume
                    buy_volume = buy_order_volume_by_price.pop(order_price)
                    volume_by_bought_prices[order_price] = buy_volume
                    remaining_sell_volume -= buy_volume
                if remaining_sell_volume <= 0:
                    break
            if volume_by_bought_prices:
                # use total_bought_volume only to avoid taking pre-existing open positions into account
                # (ex if started with already 10 btc)
                # total obtained (in ref market) – sell order fees – buy costs (in ref market before fees)
                buy_cost = sum(price * volume for price, volume in volume_by_bought_prices.items())
                fees = trade[commons_enums.DBRows.FEES_AMOUNT.value]
                fees_multiplier = 1 if trade[commons_enums.DBRows.FEES_CURRENCY.value] == ref_market \
                    else trade[commons_enums.PlotAttributes.Y.value]
                sell_fees += fees * fees_multiplier
                local_pnl = trade[commons_enums.PlotAttributes.Y.value] * \
                            trade_volume - (fees * fees_multiplier) - buy_cost
                pnl_data.append(local_pnl)
                cumulative_pnl_data.append(local_pnl + cumulative_pnl_data[-1])
                if x_as_trade_count:
                    x_data.append(len(pnl_data) - 1)
                else:
                    x_data.append(trade[commons_enums.PlotAttributes.X.value])
        else:
            get_logger().error(f"Unknown trade side: {trade}")


def _read_pnl_from_transactions(x_data, pnl_data, cumulative_pnl_data, trading_transactions_history, x_as_trade_count):
    previous_value = 0
    for transaction in trading_transactions_history:
        transaction_pnl = 0 if transaction["realised_pnl"] is None else transaction["realised_pnl"]
        transaction_quantity = 0 if transaction["quantity"] is None else transaction["quantity"]
        local_quantity = transaction_pnl + transaction_quantity
        cumulated_pnl = local_quantity + previous_value
        pnl_data.append(local_quantity)
        cumulative_pnl_data.append(cumulated_pnl)
        previous_value = cumulated_pnl
        if x_as_trade_count:
            x_data.append(len(pnl_data) - 1)
        else:
            x_data.append(transaction[commons_enums.PlotAttributes.X.value])


async def _get_historical_pnl(meta_database, plotted_element, include_cumulative, include_unitary,
                              exchange=None, x_as_trade_count=True, own_yaxis=False, historical_values=None):
    # PNL:
    # 1. open position: consider position opening fee from PNL
    # 2. close position: consider closed amount + closing fee into PNL
    # what is a trade ?
    #   futures: when position going to 0 (from long/short) => trade is closed
    #   spot: when position lowered => trade is closed
    price_data, trades_data, _, _, _, _ = historical_values or await load_historical_values(meta_database, exchange)
    if not (price_data and next(iter(price_data.values()))):
        return
    x_data = [0 if x_as_trade_count
              else next(iter(price_data.values()))[0][commons_enums.PriceIndexes.IND_PRICE_TIME.value]]
    pnl_data = [0]
    cumulative_pnl_data = [0]
    trading_transactions_history = await get_transactions(
        meta_database,
        transaction_types=(trading_enums.TransactionType.TRADING_FEE.value,
                           trading_enums.TransactionType.FUNDING_FEE.value,
                           trading_enums.TransactionType.REALISED_PNL.value,
                           trading_enums.TransactionType.CLOSE_REALISED_PNL.value)
    )
    if trading_transactions_history:
        # can rely on pnl history
        _read_pnl_from_transactions(x_data, pnl_data, cumulative_pnl_data,
                                    trading_transactions_history, x_as_trade_count)
    else:
        # recreate pnl history from trades
        _read_pnl_from_trades(x_data, pnl_data, cumulative_pnl_data, trades_data, x_as_trade_count)

    if not x_as_trade_count:
        # x axis is time: add a value at the end of the axis if missing to avoid a missing values at the end feeling
        last_time_value = next(iter(price_data.values()))[-1][commons_enums.PriceIndexes.IND_PRICE_TIME.value]
        if x_data[-1] != last_time_value:
            # append the latest value at the end of the x axis
            x_data.append(last_time_value)
            pnl_data.append(0)
            cumulative_pnl_data.append(cumulative_pnl_data[-1])

    if include_unitary:
        plotted_element.plot(
            kind="bar",
            x=x_data,
            y=pnl_data,
            x_type="tick0" if x_as_trade_count else "date",
            title="P&L per trade",
            own_yaxis=own_yaxis)

    if include_cumulative:
        plotted_element.plot(
            mode="scatter",
            x=x_data,
            y=cumulative_pnl_data,
            x_type="tick0" if x_as_trade_count else "date",
            title="Cumulative P&L",
            own_yaxis=own_yaxis,
            line_shape="hv")


async def total_paid_fees(meta_database, all_trades):
    paid_fees = 0
    fees_currency = None
    trading_transactions_history = await get_transactions(
        meta_database,
        transaction_types=(trading_enums.TransactionType.FUNDING_FEE.value,)
    )
    if trading_transactions_history:
        for transaction in trading_transactions_history:
            if fees_currency is None:
                fees_currency = transaction["currency"]
            if transaction["currency"] != fees_currency:
                get_logger().error(f"Unknown funding fee value: {transaction}")
            else:
                # - because funding fees are stored as negative number when paid (positive when "gained")
                paid_fees -= transaction["quantity"]
    for trade in all_trades:
        currency = symbol_util.parse_symbol(trade[commons_enums.DBRows.SYMBOL.value]).base
        if trade[commons_enums.DBRows.FEES_CURRENCY.value] == currency:
            if trade[commons_enums.DBRows.FEES_CURRENCY.value] == fees_currency:
                paid_fees += trade[commons_enums.DBRows.FEES_AMOUNT.value]
            else:
                paid_fees += trade[commons_enums.DBRows.FEES_AMOUNT.value] * \
                             trade[commons_enums.PlotAttributes.Y.value]
        else:
            if trade[commons_enums.DBRows.FEES_CURRENCY.value] == fees_currency:
                paid_fees += trade[commons_enums.DBRows.FEES_AMOUNT.value] / \
                             trade[commons_enums.PlotAttributes.Y.value]
            else:
                paid_fees += trade[commons_enums.DBRows.FEES_AMOUNT.value]
    return paid_fees


async def plot_historical_pnl_value(meta_database, plotted_element, exchange=None, x_as_trade_count=True,
                                    own_yaxis=False, include_cumulative=True, include_unitary=True,
                                    historical_values=None):
    return await _get_historical_pnl(meta_database, plotted_element, include_cumulative, include_unitary,
                                     exchange=exchange, x_as_trade_count=x_as_trade_count, own_yaxis=own_yaxis,
                                     historical_values=historical_values)


def _plot_table_data(data, plotted_element, data_name, additional_key_to_label, additional_columns,
                     datum_columns_callback):
    if not data:
        get_logger().debug(f"Nothing to create a table from when reading {data_name}")
        return
    column_render = _get_default_column_render()
    types = _get_default_types()
    key_to_label = {
        **plotted_element.TABLE_KEY_TO_COLUMN,
        **additional_key_to_label
    }
    columns = _get_default_columns(plotted_element, data, column_render, key_to_label) + additional_columns
    if datum_columns_callback:
        for datum in data:
            datum_columns_callback(datum)
    rows = _get_default_rows(data, columns)
    searches = _get_default_searches(columns, types)
    plotted_element.table(
        data_name,
        columns=columns,
        rows=rows,
        searches=searches
    )


async def plot_trades(meta_database, plotted_element, historical_values=None):
    if historical_values:
        _, trades_data, _, _, _, _ = historical_values
        data = []
        for trades in trades_data.values():
            data += trades
    else:
        account_type = trading_api.get_account_type_from_run_metadata(await get_metadata(meta_database))
        data = await meta_database.get_trades_db(account_type).all(commons_enums.DBTables.TRADES.value)
    key_to_label = {
        commons_enums.PlotAttributes.Y.value: "Price",
        commons_enums.PlotAttributes.TYPE.value: "Type",
        commons_enums.PlotAttributes.SIDE.value: "Side",
    }
    additional_columns = [
        {
            "field": "total",
            "label": "Total",
            "render": None
        }, {
            "field": "fees",
            "label": "Fees",
            "render": None
        }
    ]

    def datum_columns_callback(datum):
        datum["total"] = datum["cost"]
        datum["fees"] = f'{datum["fees_amount"]} {datum["fees_currency"]}'

    _plot_table_data(data, plotted_element, commons_enums.DBTables.TRADES.value,
                     key_to_label, additional_columns, datum_columns_callback)


async def plot_orders(meta_database, plotted_element, historical_values=None):
    if historical_values:
        _, _, _, _, metadata, _ = historical_values
    else:
        metadata = await get_metadata(meta_database)
    account_type = trading_api.get_account_type_from_run_metadata(metadata)
    data = [
        order[trading_constants.STORAGE_ORIGIN_VALUE]
        for order in await meta_database.get_orders_db(account_type).all(commons_enums.DBTables.ORDERS.value)
    ]
    key_to_label = {
        trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: "Time",
        trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "Price",
        trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: "Amount",
        trading_enums.ExchangeConstantsOrderColumns.TYPE.value: "Type",
        trading_enums.ExchangeConstantsOrderColumns.SIDE.value: "Side",
    }
    additional_columns = [
        {
            "field": "total",
            "label": "Total",
            "render": None
        }
    ]

    def datum_columns_callback(datum):
        datum["total"] = datum[trading_enums.ExchangeConstantsOrderColumns.COST.value]
        datum[trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value] *= 1000

    _plot_table_data(data, plotted_element, commons_enums.DBTables.ORDERS.value,
                     key_to_label, additional_columns, datum_columns_callback)


async def plot_withdrawals(meta_database, plotted_element):
    withdrawal_history = await get_transactions(
        meta_database,
        transaction_types=(trading_enums.TransactionType.BLOCKCHAIN_WITHDRAWAL.value,)
    )
    # apply quantity to y for each withdrawal
    for withdrawal in withdrawal_history:
        withdrawal[commons_enums.PlotAttributes.Y.value] = withdrawal["quantity"]
    key_to_label = {
        commons_enums.PlotAttributes.Y.value: "Quantity",
        "currency": "Currency",
        commons_enums.PlotAttributes.SIDE.value: "Side",
    }
    additional_columns = []

    _plot_table_data(withdrawal_history, plotted_element, "Withdrawals",
                     key_to_label, additional_columns, None)


async def plot_positions(meta_database, plotted_element):
    realized_pnl_history = await get_transactions(
        meta_database,
        transaction_types=(trading_enums.TransactionType.CLOSE_REALISED_PNL.value,)
    )
    key_to_label = {
        commons_enums.PlotAttributes.X.value: "Exit time",
        "first_entry_time": "Entry time",
        "average_entry_price": "Average entry price",
        "average_exit_price": "Average exit price",
        "cumulated_closed_quantity": "Cumulated closed quantity",
        "realised_pnl": "Realised PNL",
        commons_enums.PlotAttributes.SIDE.value: "Side",
        "trigger_source": "Closed by",
    }

    _plot_table_data(realized_pnl_history, plotted_element, "Positions", key_to_label, [], None)


async def display(plotted_element, label, value):
    plotted_element.value(label, value)


async def display_html(plotted_element, html):
    plotted_element.html_value(html)


async def plot_table(meta_database, plotted_element, data_source, columns=None, rows=None,
                     searches=None, column_render=None, types=None, cache_value=None):
    data = []
    metadata = await get_metadata(meta_database)
    account_type = trading_api.get_account_type_from_run_metadata(metadata)
    if data_source == commons_enums.DBTables.TRADES.value:
        data = await meta_database.get_trades_db(account_type).all(commons_enums.DBTables.TRADES.value)
    elif data_source == commons_enums.DBTables.ORDERS.value:
        data = await meta_database.get_orders_db(account_type).all(commons_enums.DBTables.ORDERS.value)
    else:
        exchange = meta_database.run_dbs_identifier.context.exchange_name
        symbol = meta_database.run_dbs_identifier.context.symbol
        symbol_db = meta_database.get_symbol_db(exchange, symbol)
        if cache_value is None:
            data = await symbol_db.all(data_source)
        else:
            query = (await symbol_db.search()).title == data_source
            cache_data = await symbol_db.select(commons_enums.DBTables.CACHE_SOURCE.value, query)
            if cache_data:
                try:
                    cache_database = databases.CacheDatabase(cache_data[0][commons_enums.PlotAttributes.VALUE.value])
                    cache = await cache_database.get_cache()
                    x_shift = cache_data[0]["x_shift"]
                    data = [
                        {
                            commons_enums.PlotAttributes.X.value: (cache_element[commons_enums.CacheDatabaseColumns.TIMESTAMP.value] + x_shift) * 1000,
                            commons_enums.PlotAttributes.Y.value: cache_element[cache_value]
                        }
                        for cache_element in cache
                    ]
                except KeyError as e:
                    get_logger().warning(f"Missing cache values when plotting data: {e}")
                except commons_errors.DatabaseNotFoundError as e:
                    get_logger().warning(f"Missing cache values when plotting data: {e}")

    if not data:
        get_logger().debug(f"Nothing to create a table from when reading {data_source}")
        return
    column_render = column_render or _get_default_column_render()
    types = types or _get_default_types()
    columns = columns or _get_default_columns(plotted_element, data, column_render)
    rows = rows or _get_default_rows(data, columns)
    searches = searches or _get_default_searches(columns, types)
    plotted_element.table(
        data_source,
        columns=columns,
        rows=rows,
        searches=searches)


def _get_default_column_render():
    return {
        "Time": "datetime",
        "Entry time": "datetime",
        "Exit time": "datetime"
    }


def _get_default_types():
    return {
        "Time": "datetime",
        "Entry time": "datetime",
        "Exit time": "datetime"
    }


def _get_default_columns(plotted_element, data, column_render, key_to_label=None):
    key_to_label = key_to_label or plotted_element.TABLE_KEY_TO_COLUMN
    return [
        {
            "field": row_key,
            "label": key_to_label[row_key],
            "render": column_render.get(key_to_label[row_key], None)
        }
        for row_key, row_value in data[0].items()
        if row_key in key_to_label and row_value is not None
    ]


def _get_default_rows(data, columns):
    column_fields = set(col["field"] for col in columns)
    return [
        {key: val for key, val in row.items() if key in column_fields}
        for row in data
    ]


def _get_default_searches(columns, types):
    return [
        {
            "field": col["field"],
            "label": col["label"],
            "type": types.get(col["label"])
        }
        for col in columns
    ]


def _get_wins_and_losses_from_transactions(x_data, wins_and_losses_data, trading_transactions_history,
                                           x_as_trade_count):
    for transaction in trading_transactions_history:
        transaction_pnl = 0 if transaction["realised_pnl"] is None else transaction["realised_pnl"]
        current_cumulative_wins = wins_and_losses_data[-1] if wins_and_losses_data else 0
        if transaction_pnl < 0:
            wins_and_losses_data.append(current_cumulative_wins - 1)
        elif transaction_pnl > 0:
            wins_and_losses_data.append(current_cumulative_wins + 1)
        else:
            continue

        if x_as_trade_count:
            x_data.append(len(wins_and_losses_data) - 1)
        else:
            x_data.append(transaction[commons_enums.PlotAttributes.X.value])


def _get_wins_and_losses_from_trades(x_data, wins_and_losses_data, trades_history, x_as_trade_count):
    # todo
    pass


async def plot_historical_wins_and_losses(meta_database, plotted_element, exchange=None, x_as_trade_count=False,
                                          own_yaxis=True, historical_values=None):
    price_data, trades_data, _, _, _, _ = historical_values or await load_historical_values(meta_database, exchange)
    if not (price_data and next(iter(price_data.values()))):
        return
    x_data = []
    wins_and_losses_data = []
    trading_transactions_history = await get_transactions(
        meta_database,
        transaction_types=(trading_enums.TransactionType.TRADING_FEE.value,
                           trading_enums.TransactionType.FUNDING_FEE.value,
                           trading_enums.TransactionType.REALISED_PNL.value,
                           trading_enums.TransactionType.CLOSE_REALISED_PNL.value)
    )
    if trading_transactions_history:
        # can rely on pnl history
        _get_wins_and_losses_from_transactions(x_data, wins_and_losses_data,
                                               trading_transactions_history, x_as_trade_count)
    else:
        # recreate pnl history from trades
        return  # todo not implemented yet
        # _read_pnl_from_trades(x_data, pnl_data, cumulative_pnl_data, trades_data, x_as_trade_count)

    plotted_element.plot(
        mode="scatter",
        x=x_data,
        y=wins_and_losses_data,
        x_type="tick0" if x_as_trade_count else "date",
        title="wins and losses count",
        own_yaxis=own_yaxis,
        line_shape="hv")


def _get_win_rates_from_transactions(x_data, win_rates_data, trading_transactions_history,
                                     x_as_trade_count):
    wins_count = 0
    losses_count = 0
    for transaction in trading_transactions_history:
        transaction_pnl = 0 if transaction["realised_pnl"] is None else transaction["realised_pnl"]
        if transaction_pnl < 0:
            losses_count += 1
        elif transaction_pnl > 0:
            wins_count += 1
        else:
            continue

        win_rates_data.append((wins_count/(losses_count+wins_count))*100)
        if x_as_trade_count:
            x_data.append(len(win_rates_data) - 1)
        else:
            x_data.append(transaction[commons_enums.PlotAttributes.X.value])


def _get_win_rates_from_trades(x_data, win_rates_data, trades_history, x_as_trade_count):
    # todo
    pass


async def plot_historical_win_rates(meta_database, plotted_element, exchange=None,
                                    x_as_trade_count=False, own_yaxis=True, historical_values=None):
    price_data, trades_data, _, _, _, _ = historical_values or await load_historical_values(meta_database, exchange)
    if not (price_data and next(iter(price_data.values()))):
        return
    x_data = []
    win_rates_data = []
    trading_transactions_history = await get_transactions(
        meta_database,
        transaction_types=(trading_enums.TransactionType.TRADING_FEE.value,
                           trading_enums.TransactionType.FUNDING_FEE.value,
                           trading_enums.TransactionType.REALISED_PNL.value,
                           trading_enums.TransactionType.CLOSE_REALISED_PNL.value)
    )
    if trading_transactions_history:
        # can rely on pnl history
        _get_win_rates_from_transactions(x_data, win_rates_data,
                                         trading_transactions_history, x_as_trade_count)
    else:
        # recreate pnl history from trades
        return  # todo not implemented yet
        # _get_win_rates_from_trades(x_data, pnl_data, cumulative_pnl_data, trades_data, x_as_trade_count)

    plotted_element.plot(
        mode="scatter",
        x=x_data,
        y=win_rates_data,
        x_type="tick0" if x_as_trade_count else "date",
        title="win rate",
        own_yaxis=own_yaxis,
        line_shape="hv")


async def _get_best_case_growth_from_transactions(trading_transactions_history,
                                                  x_as_trade_count, meta_database):
    ref_market = meta_database.run_db._database.adaptor.database.storage.cache[commons_enums.DBTables.METADATA.value]['1']['ref_market']
    start_balance = meta_database.run_db._database.adaptor.database.storage.cache[commons_enums.DBTables.PORTFOLIO.value]['1'][ref_market]['total']
    best_case_data, _, start_balance, end_balance, x_data \
        = await portfolio_util.get_coefficient_of_determination_data(transactions=trading_transactions_history,
                                                                     start_balance=start_balance,
                                                                     use_high_instead_of_end_balance=True,
                                                                     x_as_trade_count=x_as_trade_count)
    if best_case_data:
        return x_data, best_case_data
    return [], []


async def plot_best_case_growth(meta_database, plotted_element, exchange=None,
                                x_as_trade_count=False, own_yaxis=False, historical_values=None):
    price_data, trades_data, _, _, _, _ = historical_values or await load_historical_values(meta_database, exchange)
    if not (price_data and next(iter(price_data.values()))):
        return
    x_data = []
    best_case_data = []
    trading_transactions_history = await get_transactions(
        meta_database,
        transaction_types=(trading_enums.TransactionType.TRADING_FEE.value,
                           trading_enums.TransactionType.FUNDING_FEE.value,
                           trading_enums.TransactionType.REALISED_PNL.value,
                           trading_enums.TransactionType.CLOSE_REALISED_PNL.value)
    )
    if trading_transactions_history:
        # can rely on pnl history
        x_data, best_case_data = await _get_best_case_growth_from_transactions(trading_transactions_history,
                                                                               x_as_trade_count, meta_database)

    plotted_element.plot(
        mode="scatter",
        x=x_data,
        y=best_case_data,
        x_type="tick0" if x_as_trade_count else "date",
        title="best case growth",
        own_yaxis=own_yaxis,
        line_shape="hv")
