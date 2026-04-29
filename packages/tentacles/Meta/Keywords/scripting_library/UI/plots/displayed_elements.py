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

import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_commons.enums as commons_enums
import octobot_commons.errors as commons_errors
import octobot_commons.constants as commons_constants
import octobot_commons.databases as databases
import octobot_commons.display as display
import octobot_backtesting.api as backtesting_api
import octobot_trading.api as trading_api


class DisplayedElements(display.DisplayTranslator):
    TABLE_KEY_TO_COLUMN = {
        commons_enums.PlotAttributes.X.value: "Time",
        commons_enums.PlotAttributes.Y.value: "Value",
        commons_enums.PlotAttributes.Z.value: "Value",
        commons_enums.PlotAttributes.OPEN.value: "Open",
        commons_enums.PlotAttributes.HIGH.value: "High",
        commons_enums.PlotAttributes.LOW.value: "Low",
        commons_enums.PlotAttributes.CLOSE.value: "Close",
        commons_enums.PlotAttributes.VOLUME.value: "Volume",
        commons_enums.DBRows.SYMBOL.value: "Symbol",
    }

    async def fill_from_database(self, trading_mode, database_manager, exchange_name, symbol, time_frame, exchange_id,
                                 with_inputs=True, symbols=None, time_frames=None):
        async with databases.MetaDatabase.database(database_manager) as meta_db:
            graphs_by_parts = {}
            inputs = []
            candles = []
            cached_values = []
            if trading_mode.is_backtestable():
                exchange_name, symbol, time_frame = \
                    await self._adapt_inputs_for_backtesting_results(meta_db, exchange_name, symbol, time_frame)
            run_db = meta_db.get_run_db()
            metadata_rows = await run_db.all(commons_enums.DBTables.METADATA.value)
            metadata = metadata_rows[0] if metadata_rows else None
            if symbols is not None:
                symbols.extend(metadata[commons_enums.BacktestingMetadata.SYMBOLS.value])
            if time_frames is not None:
                time_frames.extend(metadata[commons_enums.BacktestingMetadata.TIME_FRAMES.value])
            account_type = trading_api.get_account_type_from_run_metadata(metadata) \
                if database_manager.is_backtesting() \
                else trading_api.get_account_type_from_exchange_manager(
                trading_api.get_exchange_manager_from_exchange_id(exchange_id)
            )
            dbs = [
                run_db,
                meta_db.get_transactions_db(account_type, exchange_name),
                meta_db.get_orders_db(account_type, exchange_name),
                meta_db.get_trades_db(account_type, exchange_name),
                meta_db.get_symbol_db(exchange_name, symbol)
            ]
            for index, db in enumerate(dbs):
                for table_name in await db.tables():
                    display_data = await db.all(table_name)
                    if table_name == commons_enums.DBTables.INPUTS.value:
                        inputs += display_data
                    if table_name == commons_enums.DBTables.CANDLES_SOURCE.value:
                        candles += display_data
                    if table_name == commons_enums.DBTables.CACHE_SOURCE.value:
                        cached_values += display_data
                    else:
                        try:
                            filter_symbol = index != len(dbs) - 1   # don't filter symbol for symbol db
                            filtered_data = self._filter_and_adapt_displayed_elements(
                                display_data, symbol, time_frame, table_name, filter_symbol
                            )
                            chart = display_data[0][commons_enums.DisplayedElementTypes.CHART.value]
                            if chart is None:
                                continue
                            if chart in graphs_by_parts:
                                graphs_by_parts[chart][table_name] = filtered_data
                            else:
                                graphs_by_parts[chart] = {table_name: filtered_data}
                        except (IndexError, KeyError):
                            # some table have no chart
                            pass
            try:
                run_start_time, run_end_time = await self._get_run_window(meta_db.get_run_db())
            except IndexError:
                run_start_time = run_end_time = 0
            first_candle_time, last_candle_time = \
                await self._add_candles(graphs_by_parts, candles, exchange_name, exchange_id, symbol, time_frame,
                                        run_start_time, run_end_time)
            await self._add_cached_values(graphs_by_parts, cached_values, time_frame,
                                          first_candle_time, last_candle_time)
            self._plot_graphs(graphs_by_parts)
            if with_inputs:
                with self.part(commons_enums.DBTables.INPUTS.value,
                               element_type=commons_enums.DisplayedElementTypes.INPUT.value) as part:
                    self.add_user_inputs(inputs, part)

    async def _adapt_inputs_for_backtesting_results(self, meta_db, exchange_name, symbol, time_frame):
        if not await meta_db.run_dbs_identifier.exchange_base_identifier_exists(exchange_name):
            single_exchange = await meta_db.run_dbs_identifier.get_single_existing_exchange()
            if single_exchange is None:
                # no single exchange with data
                raise commons_errors.MissingExchangeDataError(
                    f"No data for {exchange_name}. This run might have happened on other exchange(s)"
                )
            else:
                # retarget exchange_name
                exchange_name = single_exchange
        if not await meta_db.run_dbs_identifier.symbol_base_identifier_exists(exchange_name, symbol):
            run_metadata = await meta_db.get_run_db().all(commons_enums.DBTables.METADATA.value)
            try:
                symbols = run_metadata[0].get(commons_enums.DBRows.SYMBOLS.value, [])
                if len(symbols) > 0:
                    # retarget symbol
                    symbol = symbols[0]
                else:
                    # no single exchange with data
                    raise commons_errors.MissingExchangeDataError(
                        f"No symbol related data for {exchange_name}"
                    )
            except IndexError:
                # no run metadata, try to continue
                pass
        return exchange_name, symbol, time_frame

    def _plot_graphs(self, graphs_by_parts):
        for part, datasets in graphs_by_parts.items():
            with self.part(part, element_type=commons_enums.DisplayedElementTypes.CHART.value) as part:
                for title, dataset in datasets.items():
                    if not dataset:
                        continue
                    x = []
                    y = []
                    open = []
                    high = []
                    low = []
                    close = []
                    volume = []
                    text = []
                    color = []
                    size = []
                    shape = []
                    if dataset[0].get(commons_enums.PlotAttributes.X.value, None) is None:
                        x = None
                    if dataset[0].get(commons_enums.PlotAttributes.Y.value, None) is None:
                        y = None
                    if dataset[0].get(commons_enums.PlotAttributes.OPEN.value, None) is None:
                        open = None
                    if dataset[0].get(commons_enums.PlotAttributes.HIGH.value, None) is None:
                        high = None
                    if dataset[0].get(commons_enums.PlotAttributes.LOW.value, None) is None:
                        low = None
                    if dataset[0].get(commons_enums.PlotAttributes.CLOSE.value, None) is None:
                        close = None
                    if dataset[0].get(commons_enums.PlotAttributes.VOLUME.value, None) is None:
                        volume = None
                    if dataset[0].get(commons_enums.PlotAttributes.TEXT.value, None) is None:
                        text = None
                    if dataset[0].get(commons_enums.PlotAttributes.COLOR.value, None) is None:
                        color = None
                    if dataset[0].get(commons_enums.PlotAttributes.SIZE.value, None) is None:
                        size = None
                    if dataset[0].get(commons_enums.PlotAttributes.SHAPE.value, None) is None:
                        shape = None
                    own_yaxis = dataset[0].get(commons_enums.PlotAttributes.OWN_YAXIS.value, False)
                    for data in dataset:
                        if x is not None:
                            x.append(data[commons_enums.PlotAttributes.X.value])
                        if y is not None:
                            y.append(data[commons_enums.PlotAttributes.Y.value])
                        if open is not None:
                            open.append(data[commons_enums.PlotAttributes.OPEN.value])
                        if high is not None:
                            high.append(data[commons_enums.PlotAttributes.HIGH.value])
                        if low is not None:
                            low.append(data[commons_enums.PlotAttributes.LOW.value])
                        if close is not None:
                            close.append(data[commons_enums.PlotAttributes.CLOSE.value])
                        if volume is not None:
                            volume.append(data[commons_enums.PlotAttributes.VOLUME.value])
                        if text is not None:
                            text.append(data[commons_enums.PlotAttributes.TEXT.value])
                        if color is not None:
                            color.append(data[commons_enums.PlotAttributes.COLOR.value])
                        if size is not None:
                            size.append(data[commons_enums.PlotAttributes.SIZE.value])
                        if shape is not None:
                            shape.append(data[commons_enums.PlotAttributes.SHAPE.value])
                    # use log scale for all positive charts
                    y_type = None
                    if title == commons_enums.DBTables.CANDLES_SOURCE.value \
                            or 0 <= min(d.get(commons_enums.PlotAttributes.Y.value, 0) for d in dataset):
                        y_type = "log"

                    part.plot(
                        kind=data.get(commons_enums.PlotAttributes.KIND.value, None),
                        x=x,
                        y=y,
                        open=open,
                        high=high,
                        low=low,
                        close=close,
                        volume=volume,
                        title=title,
                        text=text,
                        x_type="date",
                        y_type=y_type,
                        mode=data.get(commons_enums.PlotAttributes.MODE.value, None),
                        own_yaxis=own_yaxis,
                        color=color,
                        size=size,
                        symbol=shape)

    def _adapt_for_display(self, table_name, filtered_elements):
        if table_name == commons_enums.DBTables.TRANSACTIONS.value:
            # only display liquidations
            filtered_elements = [
                display_element
                for display_element in filtered_elements
                if display_element.get("trigger_source", None) == trading_enums.PNLTransactionSource.LIQUIDATION.value
            ]
            for display_element in filtered_elements:
                display_element[commons_enums.PlotAttributes.COLOR.value] = "red"
                display_element[commons_enums.PlotAttributes.SHAPE.value] = commons_enums.PlotAttributes.X.value
                display_element[commons_enums.PlotAttributes.SIZE.value] = 15
                display_element[commons_enums.PlotAttributes.TEXT.value] = f"Liquidation ({abs(display_element.get('closed_quantity', 0))} liquidated)"
                display_element[commons_enums.PlotAttributes.Y.value] = display_element["order_exit_price"]
        elif table_name == commons_enums.DBTables.ORDERS.value:
            # adapt order details for display
            for display_element in filtered_elements:
                order_details = display_element[trading_constants.STORAGE_ORIGIN_VALUE]
                side = order_details[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
                display_element[commons_enums.PlotAttributes.COLOR.value] = "red" \
                    if side == trading_enums.TradeOrderSide.SELL.value else "green"
                display_element[commons_enums.PlotAttributes.SHAPE.value] = "line-ew-open"
                display_element[commons_enums.PlotAttributes.MODE.value] = "markers"
                display_element[commons_enums.PlotAttributes.KIND.value] = "scattergl"
                display_element[commons_enums.PlotAttributes.SIZE.value] = 15
                display_element[commons_enums.PlotAttributes.TEXT.value] = \
                    f"{order_details[trading_enums.ExchangeConstantsOrderColumns.TYPE.value]} " \
                    f"{order_details[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value]} " \
                    f"{order_details[trading_enums.ExchangeConstantsOrderColumns.QUANTITY_CURRENCY.value]} " \
                    f"at {order_details[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]}"
                display_element[commons_enums.PlotAttributes.Y.value] = \
                    order_details[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]
                display_element[commons_enums.PlotAttributes.X.value] = \
                    order_details[trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value] * 1000
                display_element[commons_enums.DisplayedElementTypes.CHART.value] = \
                    commons_enums.PlotCharts.MAIN_CHART.value
        return filtered_elements

    def _filter_and_adapt_displayed_elements(self, elements, symbol, time_frame, table_name, filter_symbol):
        default_symbol = None if filter_symbol else symbol
        filtered_elements = [
            display_element
            for display_element in elements
            if (
                display_element.get(commons_enums.DBRows.SYMBOL.value, default_symbol) == symbol
                and display_element.get(commons_enums.DBRows.TIME_FRAME.value) == time_frame
            ) or (
                display_element.get(trading_constants.STORAGE_ORIGIN_VALUE, {})
                .get(trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value, default_symbol) == symbol
            )
        ]
        return self._adapt_for_display(table_name, filtered_elements)

    async def _get_run_window(self, run_database):
        run_metadata = (await run_database.all(commons_enums.DBTables.METADATA.value))[0]
        end_time = run_metadata.get("end_time", 0)
        if end_time == -1:
            # live mode
            return 0, 0
        return run_metadata.get("start_time", 0), end_time

    async def _add_cached_values(self, graphs_by_parts, cached_values, time_frame, start_time, end_time):
        start_time = start_time
        end_time = end_time
        for cached_value_metadata in cached_values:
            if cached_value_metadata.get(commons_enums.DBRows.TIME_FRAME.value, None) == time_frame:
                try:
                    chart = cached_value_metadata[commons_enums.DisplayedElementTypes.CHART.value]
                    x_shift = cached_value_metadata["x_shift"]
                    values = sorted(await self._get_cached_values_to_display(cached_value_metadata, x_shift,
                                                                             start_time, end_time),
                                    key=lambda x: x[commons_enums.PlotAttributes.X.value])
                    try:
                        graphs_by_parts[chart][cached_value_metadata[commons_enums.PlotAttributes.TITLE.value]] = values
                    except KeyError:
                        if chart not in graphs_by_parts:
                            graphs_by_parts[chart] = {}
                        try:
                            graphs_by_parts[chart] = \
                                {cached_value_metadata[commons_enums.PlotAttributes.TITLE.value]: values}
                        except KeyError:
                            graphs_by_parts[chart] = {commons_enums.PlotAttributes.TITLE.value: values}
                except KeyError:
                    # some table have no chart
                    pass

    async def _get_cached_values_to_display(self, cached_value_metadata, x_shift, start_time, end_time):
        cache_file = cached_value_metadata[commons_enums.PlotAttributes.VALUE.value]
        cache_displayed_value = plotted_displayed_value = cached_value_metadata["cache_value"]
        kind = cached_value_metadata[commons_enums.PlotAttributes.KIND.value]
        mode = cached_value_metadata[commons_enums.PlotAttributes.MODE.value]
        own_yaxis = cached_value_metadata[commons_enums.PlotAttributes.OWN_YAXIS.value]
        condition = cached_value_metadata.get("condition", None)
        try:
            cache_database = databases.CacheDatabase(cache_file)
            cache_type = (await cache_database.get_metadata())[commons_enums.CacheDatabaseColumns.TYPE.value]
            if cache_type == databases.CacheTimestampDatabase.__name__:
                cache = await cache_database.get_cache()
                for cache_val in cache:
                    try:
                        if isinstance(cache_val[cache_displayed_value], bool):
                            plotted_displayed_value = self._get_cache_displayed_value(cache_val, cache_displayed_value)
                            if plotted_displayed_value is None:
                                self.logger.error(f"Impossible to plot {cache_displayed_value}: unset y axis value")
                                return []
                        else:
                            break
                    except KeyError:
                        pass
                    except Exception as e:
                        print(e)
                plotted_values = []
                for values in cache:
                    try:
                        if condition is None or condition == values[cache_displayed_value]:
                            x = (values[commons_enums.CacheDatabaseColumns.TIMESTAMP.value] + x_shift) * 1000
                            if (start_time == end_time == 0) or start_time <= x <= end_time:
                                y = values[plotted_displayed_value]
                                if not isinstance(x, list) and isinstance(y, list):
                                    for y_val in y:
                                        plotted_values.append({
                                            commons_enums.PlotAttributes.X.value: x,
                                            commons_enums.PlotAttributes.Y.value: y_val,
                                            commons_enums.PlotAttributes.KIND.value: kind,
                                            commons_enums.PlotAttributes.MODE.value: mode,
                                            commons_enums.PlotAttributes.OWN_YAXIS.value: own_yaxis,
                                        })
                                else:
                                    plotted_values.append({
                                        commons_enums.PlotAttributes.X.value: x,
                                        commons_enums.PlotAttributes.Y.value: y,
                                        commons_enums.PlotAttributes.KIND.value: kind,
                                        commons_enums.PlotAttributes.MODE.value: mode,
                                        commons_enums.PlotAttributes.OWN_YAXIS.value: own_yaxis,
                                    })
                    except KeyError:
                        pass
                return plotted_values
            self.logger.error(f"Unhandled cache type to display: {cache_type}")
        except TypeError:
            self.logger.error(f"Missing cache type in {cache_file} metadata file")
        except commons_errors.DatabaseNotFoundError as ex:
            self.logger.warning(f"Missing cache values ({ex})")
        return []

    @staticmethod
    def _get_cache_displayed_value(cache_val, base_displayed_value):
        for key in cache_val.keys():
            separator_split_key = key.split(commons_constants.CACHE_RELATED_DATA_SEPARATOR)
            if base_displayed_value == separator_split_key[0] and len(separator_split_key) == 2:
                return key
        return None

    async def _add_candles(self, graphs_by_parts, candles_list, exchange_name, exchange_id, symbol, time_frame,
                           run_start_time, run_end_time):
        first_candle_time = last_candle_time = 0
        for candles_metadata in candles_list:
            if candles_metadata.get(commons_enums.DBRows.TIME_FRAME.value) == time_frame:
                try:
                    chart = candles_metadata[commons_enums.DisplayedElementTypes.CHART.value]
                    candles = await self._get_candles_to_display(candles_metadata, exchange_name,
                                                                 exchange_id, symbol, time_frame,
                                                                 run_start_time, run_end_time)
                    try:
                        graphs_by_parts[chart][commons_enums.DBTables.CANDLES.value] = candles
                    except KeyError:
                        graphs_by_parts[chart] = {commons_enums.DBTables.CANDLES.value: candles}
                    # candles are assumed to be ordered
                    if first_candle_time == 0 or first_candle_time < candles[0][commons_enums.PlotAttributes.X.value]:
                        first_candle_time = candles[0][commons_enums.PlotAttributes.X.value]
                    if last_candle_time == 0 or last_candle_time > candles[-1][commons_enums.PlotAttributes.X.value]:
                        last_candle_time = candles[-1][commons_enums.PlotAttributes.X.value]
                except KeyError:
                    # some table have no chart
                    pass
        return first_candle_time, last_candle_time

    async def _get_candles_to_display(self, candles_metadata, exchange_name, exchange_id, symbol, time_frame,
                                      run_start_time, run_end_time):
        if candles_metadata[commons_enums.DBRows.VALUE.value] == commons_constants.LOCAL_BOT_DATA:
            exchange_manager = trading_api.get_exchange_manager_from_exchange_id(exchange_id)
            array_candles = trading_api.get_symbol_historical_candles(
                trading_api.get_symbol_data(exchange_manager, symbol, allow_creation=False), time_frame
            )
            return [
                {
                    commons_enums.PlotAttributes.X.value: time * 1000,
                    commons_enums.PlotAttributes.OPEN.value: array_candles[commons_enums.PriceIndexes.IND_PRICE_OPEN.value][index],
                    commons_enums.PlotAttributes.HIGH.value: array_candles[commons_enums.PriceIndexes.IND_PRICE_HIGH.value][index],
                    commons_enums.PlotAttributes.LOW.value: array_candles[commons_enums.PriceIndexes.IND_PRICE_LOW.value][index],
                    commons_enums.PlotAttributes.CLOSE.value: array_candles[commons_enums.PriceIndexes.IND_PRICE_CLOSE.value][index],
                    commons_enums.PlotAttributes.VOLUME.value: array_candles[commons_enums.PriceIndexes.IND_PRICE_VOL.value][index],
                    commons_enums.PlotAttributes.KIND.value: "candlestick",
                    commons_enums.PlotAttributes.MODE.value: "lines",
                }
                for index, time in enumerate(array_candles[commons_enums.PriceIndexes.IND_PRICE_TIME.value])
                if (run_start_time == run_end_time == 0) or run_start_time <= time <= run_end_time
            ]
        db_candles = await backtesting_api.get_all_ohlcvs(candles_metadata[commons_enums.DBRows.VALUE.value],
                                                          exchange_name,
                                                          symbol,
                                                          commons_enums.TimeFrames(time_frame),
                                                          inferior_timestamp=run_start_time if run_start_time > 0
                                                          else -1,
                                                          superior_timestamp=run_end_time if run_end_time > 0 else -1)
        return [
            {
                commons_enums.PlotAttributes.X.value: db_candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value] * 1000,
                commons_enums.PlotAttributes.OPEN.value: db_candle[commons_enums.PriceIndexes.IND_PRICE_OPEN.value],
                commons_enums.PlotAttributes.HIGH.value: db_candle[commons_enums.PriceIndexes.IND_PRICE_HIGH.value],
                commons_enums.PlotAttributes.LOW.value: db_candle[commons_enums.PriceIndexes.IND_PRICE_LOW.value],
                commons_enums.PlotAttributes.CLOSE.value: db_candle[commons_enums.PriceIndexes.IND_PRICE_CLOSE.value],
                commons_enums.PlotAttributes.VOLUME.value: db_candle[commons_enums.PriceIndexes.IND_PRICE_VOL.value],
                commons_enums.PlotAttributes.KIND.value: "candlestick",
                commons_enums.PlotAttributes.MODE.value: "lines",
            }
            for index, db_candle in enumerate(db_candles)
        ]

    def plot(
            self,
            x,
            y=None,
            open=None,
            high=None,
            low=None,
            close=None,
            volume=None,
            x_type="date",
            y_type=None,
            title=None,
            text=None,
            kind="scattergl",
            mode="lines",
            line_shape="linear",
            own_xaxis=False,
            own_yaxis=False,
            color=None,
            size=None,
            symbol=None,
    ):
        element = display.Element(
            kind,
            x,
            y,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            x_type=x_type,
            y_type=y_type,
            title=title,
            text=text,
            mode=mode,
            line_shape=line_shape,
            own_xaxis=own_xaxis,
            own_yaxis=own_yaxis,
            type=commons_enums.DisplayedElementTypes.CHART.value,
            color=color,
            size=size,
            symbol=symbol
        )
        self.elements.append(element)

    def table(
            self,
            name,
            columns,
            rows,
            searches
    ):
        element = display.Element(
            None,
            None,
            None,
            title=name,
            columns=columns,
            rows=rows,
            searches=searches,
            type=commons_enums.DisplayedElementTypes.TABLE.value
        )
        self.elements.append(element)

    def value(self, label, value):
        element = display.Element(
            None,
            None,
            None,
            title=label,
            value=str(value),
            type=commons_enums.DisplayedElementTypes.VALUE.value
        )
        self.elements.append(element)

    def html_value(self, html):
        element = display.Element(
            None,
            None,
            None,
            html=html,
            type=commons_enums.DisplayedElementTypes.VALUE.value
        )
        self.elements.append(element)
