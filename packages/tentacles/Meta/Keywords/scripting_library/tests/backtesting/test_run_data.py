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
import pytest
import mock

import tentacles.Meta.Keywords.scripting_library.backtesting.run_data_analysis as run_data_analysis
import octobot_trading.enums as trading_enums
import octobot_commons.enums as commons_enums

from tentacles.Meta.Keywords.scripting_library.tests import event_loop
from tentacles.Meta.Keywords.scripting_library.tests.backtesting.data_store import default_price_data, \
    default_trades_data, default_portfolio_data, default_portfolio_historical_value, default_pnl_historical_value, \
    default_funding_fees_data, default_realized_pnl_history, default_spot_metadata

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_plot_historical_portfolio_value(default_price_data, default_trades_data, default_portfolio_data,
                                               default_portfolio_historical_value, default_funding_fees_data,
                                               default_spot_metadata):
    expected_time_data = [candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value]
                          for candle in default_price_data["BTC/USDT"]]
    await _test_historical_portfolio_values(default_price_data, default_trades_data, default_portfolio_data,
                                            default_funding_fees_data, expected_time_data,
                                            default_portfolio_historical_value,
                                            "spot",
                                            default_spot_metadata)


async def test_get_historical_pnl(default_price_data, default_trades_data, default_pnl_historical_value,
                                  default_realized_pnl_history, default_spot_metadata):
    # expected_time_data start at the 1st time data with a default_pnl_historical_value at 0
    expected_time_data = \
        [default_price_data["BTC/USDT"][0][commons_enums.PriceIndexes.IND_PRICE_TIME.value]] + \
        [trade[commons_enums.PlotAttributes.X.value]
         for trade in default_trades_data["BTC/USDT"]
         if trade[commons_enums.PlotAttributes.SIDE.value] == trading_enums.TradeOrderSide.SELL.value] + \
        [default_price_data["BTC/USDT"][-1][commons_enums.PriceIndexes.IND_PRICE_TIME.value]]
    cumulative_pnl_historical_value = [default_pnl_historical_value[0]]
    for value in default_pnl_historical_value[1:]:
        cumulative_pnl_historical_value.append(cumulative_pnl_historical_value[-1] + value)
    await _test_historical_pnl_values_from_trades(default_price_data, default_trades_data, [], False, True, False,
                                                  expected_time_data, default_pnl_historical_value,
                                                  cumulative_pnl_historical_value,
                                                  "spot", default_spot_metadata)

    expected_time_data = [i for i in range(len(cumulative_pnl_historical_value))]
    await _test_historical_pnl_values_from_trades(default_price_data, default_trades_data, default_realized_pnl_history,
                                                  True, True, True, expected_time_data, default_pnl_historical_value,
                                                  cumulative_pnl_historical_value,
                                                  "spot", default_spot_metadata)
    await _test_historical_pnl_values_from_trades(default_price_data, default_trades_data, default_realized_pnl_history,
                                                  False, False, True, expected_time_data, default_pnl_historical_value,
                                                  cumulative_pnl_historical_value,
                                                  "spot", default_spot_metadata)


async def test_total_paid_fees(default_trades_data):
    usdt_fees = sum(trade[commons_enums.DBRows.FEES_AMOUNT.value]
                    for trade in default_trades_data["BTC/USDT"]
                    if trade[commons_enums.DBRows.FEES_CURRENCY.value] == "USDT")
    btc_fees_in_usdt = sum(trade[commons_enums.DBRows.FEES_AMOUNT.value] * trade[commons_enums.PlotAttributes.Y.value]
                           for trade in default_trades_data["BTC/USDT"]
                           if trade[commons_enums.DBRows.FEES_CURRENCY.value] == "BTC")
    with mock.patch.object(run_data_analysis, "get_transactions",
                           mock.AsyncMock(return_value=[])) as get_transactions_mock:
        assert round(await run_data_analysis.total_paid_fees(None, default_trades_data["BTC/USDT"]), 15) == \
               round(usdt_fees + btc_fees_in_usdt, 15)
        get_transactions_mock.assert_called_once()


async def _test_historical_portfolio_values(price_data, trades_data, portfolio_data, funding_fees_data,
                                            expected_time_data, expected_value_data, exchange_type,
                                            spot_metadata):
    plotted_element = mock.Mock()
    with mock.patch.object(run_data_analysis, "load_historical_values",
                           mock.AsyncMock(return_value=(price_data, trades_data, portfolio_data, exchange_type,
                                                        spot_metadata, spot_metadata))) \
            as load_historical_values_mock, \
         mock.patch.object(run_data_analysis, "get_transactions",
                           mock.AsyncMock(return_value=funding_fees_data)) \
            as get_transactions_mock:
        await run_data_analysis.plot_historical_portfolio_value("meta_database", plotted_element,
                                                                exchange="exchange", own_yaxis=True)
        load_historical_values_mock.assert_called_once_with("meta_database", "exchange")
        get_transactions_mock.assert_called_once_with("meta_database",
                                                      transaction_type=trading_enums.TransactionType.FUNDING_FEE.value)
        plotted_element.plot.assert_called_once_with(
            mode="scatter",
            x=expected_time_data,
            y=expected_value_data,
            title="Portfolio value",
            own_yaxis=True
        )


async def _test_historical_pnl_values_from_trades(price_data, trades_data, pnl_data, include_cumulative,
                                                  include_unitary,
                                                  x_as_trade_count, expected_time_data, expected_value_data,
                                                  expected_cumulative_values,
                                                  exchange_type, spot_metadata):
    plotted_element = mock.Mock()
    with mock.patch.object(run_data_analysis, "load_historical_values",
                           mock.AsyncMock(return_value=(price_data, trades_data, None, exchange_type, spot_metadata,
                                                        spot_metadata))) \
            as load_historical_values_mock, \
         mock.patch.object(run_data_analysis, "get_transactions",
                           mock.AsyncMock(return_value=pnl_data)) \
            as get_transactions_mock:
        await run_data_analysis._get_historical_pnl("meta_database", plotted_element, include_cumulative,
                                                    include_unitary,
                                                    exchange="exchange", x_as_trade_count=x_as_trade_count,
                                                    own_yaxis=True)
        load_historical_values_mock.assert_called_once_with("meta_database", "exchange")
        get_transactions_mock.assert_called_once_with("meta_database",
                                                      transaction_types=(
                                                          trading_enums.TransactionType.TRADING_FEE.value,
                                                          trading_enums.TransactionType.FUNDING_FEE.value,
                                                          trading_enums.TransactionType.REALISED_PNL.value,
                                                          trading_enums.TransactionType.CLOSE_REALISED_PNL.value)
                                                      )
        if include_cumulative:
            assert plotted_element.plot.call_count == 2
        else:
            if include_unitary:
                plotted_element.plot.assert_called_once_with(
                    kind="bar",
                    x=expected_time_data,
                    y=expected_value_data,
                    x_type="tick0" if x_as_trade_count else "date",
                    title="P&L per trade",
                    own_yaxis=True
                )
            else:
                plotted_element.assert_not_called()
