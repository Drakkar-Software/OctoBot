#  Drakkar-Software OctoBot-Trading
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
import os
import sortedcontainers
import decimal

import octobot_commons.enums as commons_enums
import octobot_trading.personal_data as personal_data
import octobot_trading.constants as constants

from tests.exchanges import backtesting_trader_with_historical_pf_value_manager, \
    backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting
from tests import event_loop

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def historical_portfolio_value_manager(backtesting_trader_with_historical_pf_value_manager):
    config, exchange_manager, trader = backtesting_trader_with_historical_pf_value_manager
    return exchange_manager.exchange_personal_data.portfolio_manager.historical_portfolio_value_manager


async def test_constructor(historical_portfolio_value_manager):
    assert historical_portfolio_value_manager is not None
    assert historical_portfolio_value_manager.portfolio_manager is not None
    assert historical_portfolio_value_manager.saved_time_frames == constants.DEFAULT_SAVED_HISTORICAL_TIMEFRAMES
    assert historical_portfolio_value_manager.historical_portfolio_value == sortedcontainers.SortedDict()
    assert historical_portfolio_value_manager.starting_time is not None
    assert historical_portfolio_value_manager.starting_time == historical_portfolio_value_manager.last_update_time
    assert historical_portfolio_value_manager.starting_portfolio is None
    assert historical_portfolio_value_manager.ending_portfolio is None


async def test_initialize(historical_portfolio_value_manager):
    # run_dbs_identifier is None: does nothing
    await historical_portfolio_value_manager.initialize()
    assert historical_portfolio_value_manager.historical_portfolio_value == sortedcontainers.SortedDict()

    with mock.patch.object(historical_portfolio_value_manager, "_reload_historical_portfolio_value", mock.AsyncMock()) \
         as _reload_historical_portfolio_value_mock:
        historical_portfolio_value_manager.is_initialized = False
        await historical_portfolio_value_manager.initialize()
        _reload_historical_portfolio_value_mock.assert_not_called()

        try:
            historical_portfolio_value_manager.portfolio_manager.exchange_manager.is_backtesting = False
            historical_portfolio_value_manager.is_initialized = False
            await historical_portfolio_value_manager.initialize()
            _reload_historical_portfolio_value_mock.assert_called_once()
        finally:
            # restore value
            historical_portfolio_value_manager.portfolio_manager.exchange_manager.is_backtesting = True


async def test_on_new_value(historical_portfolio_value_manager):
    timestamp = 1648462965  # Monday 28 March 2022 10:22:45 UTC
    exchange_time = timestamp + 10
    day_timestamp = 1648425600  # Monday 28 March 2022 00:00:00 UTC
    # force exchange current time
    historical_portfolio_value_manager.portfolio_manager.exchange_manager.exchange.connector.backtesting.\
        time_manager.current_timestamp = exchange_time
    value_by_currency = {
        "BTC": 1,
        "USD": 3000
    }

    # new timestamp, too late in the day, ignore it
    too_late_timestamp = 1648504800  # Monday 28 March 2022 22:00:00 UTC
    assert await historical_portfolio_value_manager.on_new_value(too_late_timestamp, value_by_currency,
                                                                 save_changes=False) is False
    assert historical_portfolio_value_manager.historical_portfolio_value == sortedcontainers.SortedDict()

    # new timestamp early enough in the day, add it
    assert await historical_portfolio_value_manager.on_new_value(timestamp, value_by_currency,
                                                                 save_changes=False) is True
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [day_timestamp]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            day_timestamp, value_by_currency)

    # new currency value, same time
    value_by_currency_2 = {
        "BTC": 1,
        "USD": 3000,
        "HELLO": 666
    }
    assert await historical_portfolio_value_manager.on_new_value(timestamp, value_by_currency_2,
                                                                 save_changes=False) is True
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [day_timestamp]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            day_timestamp, value_by_currency_2)

    # change currency value (minor value change), same time
    value_by_currency_3 = {
        "BTC": 1,
        "USD": 3001,
        "HELLO": 666
    }
    # no force update: no change
    assert await historical_portfolio_value_manager.on_new_value(timestamp, value_by_currency_3,
                                                                 save_changes=False) is False
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [day_timestamp]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            day_timestamp, value_by_currency_2)

    # change currency value (major value change), same time
    value_by_currency_major_change = {
        "BTC": 2.5,
        "USD": 3001,
        "HELLO": 666
    }
    # major change, no force update: change even if no force
    assert await historical_portfolio_value_manager.on_new_value(
        timestamp, value_by_currency_major_change, save_changes=False) is True
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [day_timestamp]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            day_timestamp, value_by_currency_major_change)

    # force update: actual forced change
    assert await historical_portfolio_value_manager.on_new_value(timestamp, value_by_currency_3,
                                                                 save_changes=False, force_update=True) is True
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [day_timestamp]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            day_timestamp, value_by_currency_3)

    # new timestamp, same day: ignore it
    timestamp_same_day = timestamp + 1000
    assert await historical_portfolio_value_manager.on_new_value(timestamp_same_day, value_by_currency_3,
                                                                 save_changes=False) is False
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [day_timestamp]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            day_timestamp, value_by_currency_3)

    # timestamp on new day, same day: ignore
    timestamp_new_day = 1648540800  # Tuesday 29 March 2022 08:00:00
    assert await historical_portfolio_value_manager.on_new_value(timestamp_new_day, value_by_currency_3,
                                                                 save_changes=False) is False
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [day_timestamp]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            day_timestamp, value_by_currency_3)

    # force exchange current time
    new_day_timestamp = 1648512000
    new_day_exchange_time = new_day_timestamp + 3001
    historical_portfolio_value_manager.portfolio_manager.exchange_manager.exchange.connector.backtesting.\
        time_manager.current_timestamp = new_day_exchange_time
    # timestamp on new day, new day: add it
    assert await historical_portfolio_value_manager.on_new_value(timestamp_new_day, value_by_currency_3,
                                                                 save_changes=False) is True
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [day_timestamp,
                                                                                          new_day_timestamp]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            day_timestamp, value_by_currency_3)
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[1],
                            new_day_timestamp, value_by_currency_3)

    value_by_currency_4 = {
        "BTC": 9,
        "USD": 1111,
        "HELLO": 666
    }
    # force update: actual change
    assert await historical_portfolio_value_manager.on_new_value(timestamp_new_day, value_by_currency_4,
                                                                 save_changes=False, force_update=True) is True
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [day_timestamp,
                                                                                          new_day_timestamp]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            day_timestamp, value_by_currency_3)
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[1],
                            new_day_timestamp, value_by_currency_4)


async def test_on_new_value_with_max_size_reached(historical_portfolio_value_manager):
    timestamp = 1648462965  # Monday 28 March 2022 10:22:45 UTC
    exchange_time = timestamp + 10
    day_timestamp = 1648425600  # Monday 28 March 2022 00:00:00 UTC
    # force exchange current time
    historical_portfolio_value_manager.max_history_size = 2
    historical_portfolio_value_manager.portfolio_manager.exchange_manager.exchange.connector.backtesting.\
        time_manager.current_timestamp = exchange_time
    value_by_currency = {
        "BTC": decimal.Decimal(1),
        "USD": decimal.Decimal(3000)
    }
    # new timestamp early enough in the day, add it
    assert await historical_portfolio_value_manager.on_new_value(timestamp, value_by_currency,
                                                                 save_changes=False) is True
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [day_timestamp]

    new_day_timestamp = 1648512000
    timestamp_new_day = new_day_timestamp + 1
    value_by_currency_2 = {
        "BTC": decimal.Decimal(11),
        "USD": decimal.Decimal(30003)
    }
    new_day_exchange_time = new_day_timestamp + 3001
    historical_portfolio_value_manager.portfolio_manager.exchange_manager.exchange.connector.backtesting.\
        time_manager.current_timestamp = new_day_exchange_time
    # timestamp on new day, new day: add it
    assert await historical_portfolio_value_manager.on_new_value(timestamp_new_day, value_by_currency_2,
                                                                 save_changes=False) is True
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [day_timestamp,
                                                                                          new_day_timestamp]
    float_value_by_currency = {
        "BTC": 1,
        "USD": 3000
    }
    float_value_by_currency_2 = {
        "BTC": 11,
        "USD": 30003
    }
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            day_timestamp, float_value_by_currency)
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[1],
                            new_day_timestamp, float_value_by_currency_2)

    other_new_day_timestamp = 1648598400  # Wednesday 30 March 2022 00:00:00 UTC
    other_timestamp_new_day = other_new_day_timestamp + 1
    value_by_currency_3 = {
        "BTC": decimal.Decimal("111.111"),
        "USD": decimal.Decimal("300033.111")
    }
    float_value_by_currency_3 = {
        "BTC": 111.111,
        "USD": 300033.111
    }
    new_day_exchange_time = other_new_day_timestamp + 3001
    historical_portfolio_value_manager.portfolio_manager.exchange_manager.exchange.connector.backtesting.\
        time_manager.current_timestamp = new_day_exchange_time
    # timestamp on new day, new day: add it but remove the oldest one as max size is reached
    assert await historical_portfolio_value_manager.on_new_value(other_timestamp_new_day, value_by_currency_3,
                                                                 save_changes=False) is True
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [new_day_timestamp,
                                                                                          other_new_day_timestamp]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            new_day_timestamp, float_value_by_currency_2)
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[1],
                            other_new_day_timestamp, float_value_by_currency_3)


async def test_on_new_value_multiple_time_frames(historical_portfolio_value_manager):
    historical_portfolio_value_manager.saved_time_frames = [
        commons_enums.TimeFrames.ONE_DAY, commons_enums.TimeFrames.ONE_HOUR
    ]
    timestamp = 1648462965  # Monday 28 March 2022 10:22:45 UTC
    day_timestamp = 1648425600  # Monday 28 March 2022 00:00:00 UTC
    hour_timestamp = 1648461600  # Monday 28 March 2022 00:10:00 UTC
    exchange_time = timestamp + 10
    # force exchange current time
    historical_portfolio_value_manager.portfolio_manager.exchange_manager.exchange.connector.backtesting.\
        time_manager.current_timestamp = exchange_time
    value_by_currency = {
        "BTC": 1,
        "USD": 3000
    }

    too_late_timestamp = 1648504800  # Monday 28 March 2022 22:00:00 UTC
    # new timestamp, too late in the day, ignore it
    assert await historical_portfolio_value_manager.on_new_value(too_late_timestamp, value_by_currency,
                                                                 save_changes=False) is False
    assert historical_portfolio_value_manager.historical_portfolio_value == sortedcontainers.SortedDict()

    # new timestamp, too late in the day, ignore it BUT not too late for one hour time_frame
    late_hour_timestamp = 1648483200  # Monday 28 March 2022 16:00:00 UTC
    historical_portfolio_value_manager.portfolio_manager.exchange_manager.exchange.connector.backtesting.\
        time_manager.current_timestamp = late_hour_timestamp
    assert await historical_portfolio_value_manager.on_new_value(late_hour_timestamp + 1, value_by_currency,
                                                                 save_changes=False) is True
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [late_hour_timestamp]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            late_hour_timestamp, value_by_currency)

    value_by_currency_2 = {
        "BTC": 10
    }
    # new timestamp early enough in the day, add it
    historical_portfolio_value_manager.portfolio_manager.exchange_manager.exchange.connector.backtesting.\
        time_manager.current_timestamp = hour_timestamp + 3
    assert await historical_portfolio_value_manager.on_new_value(hour_timestamp + 1, value_by_currency_2,
                                                                 save_changes=False) is True
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [
        day_timestamp, hour_timestamp, late_hour_timestamp
    ]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            day_timestamp, value_by_currency_2)
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[1],
                            hour_timestamp, value_by_currency_2)
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[2],
                            late_hour_timestamp, value_by_currency)

    value_by_currency_3 = {
        "ETH": 55
    }
    # new timestamp that happens to be associated to the same time in 1h and 1d
    early_day_hour_timestamp = 1648512900  # Tuesday 29 March 2022 00:15:00 UTC
    tuesday_timestamp = 1648512000  # Tuesday 29 March 2022 00:00:00 UTC
    historical_portfolio_value_manager.portfolio_manager.exchange_manager.exchange.connector.backtesting.\
        time_manager.current_timestamp = early_day_hour_timestamp
    assert await historical_portfolio_value_manager.on_new_value(early_day_hour_timestamp + 1, value_by_currency_3,
                                                                 save_changes=False) is True
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [
        day_timestamp, hour_timestamp, late_hour_timestamp, tuesday_timestamp
    ]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            day_timestamp, value_by_currency_2)
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[1],
                            hour_timestamp, value_by_currency_2)
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[2],
                            late_hour_timestamp, value_by_currency)
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[3],
                            tuesday_timestamp, value_by_currency_3)


async def test_on_new_values(historical_portfolio_value_manager):
    timestamp = 1648462965  # Monday 28 March 2022 10:22:45 UTC
    exchange_time = timestamp + 10
    friday_timestamp = 1648166400  # Friday 25 March 2022 00:00:00
    saturday_timestamp = 1648252800  # Saturday 26 March 2022 00:00:00
    sunday_timestamp = 1648339200  # Sunday 27 March 2022 00:00:00
    today_timestamp = 1648425600  # Monday 28 March 2022 00:00:00 UTC
    # force exchange current time
    historical_portfolio_value_manager.portfolio_manager.exchange_manager.exchange.connector.backtesting.\
        time_manager.current_timestamp = exchange_time
    friday_value_by_currency = {
        "BTC": 1.1,
        "USD": 3010
    }
    saturday_value_by_currency = {
        "BTC": 1.3
    }
    sunday_value_by_currency = {
        "USD": 3
    }
    today_value_by_currency = {
        "BTC": 11,
        "USD": 54,
        "ETH": 33
    }
    # new timestamp, too late in the day, ignore it
    too_late_timestamp = 1648504800  # Monday 28 March 2022 22:00:00 UTC
    value_by_currency_by_timestamp = {
        friday_timestamp: friday_value_by_currency,     # use exact timestamps for some past timestamps
        sunday_timestamp: sunday_value_by_currency,     # on purpose out of order, value manager is supposed to sort it
        saturday_timestamp + 10: saturday_value_by_currency,
        too_late_timestamp: today_value_by_currency,    # use too_late_timestamp for today timestamp
    }
    # saves historical timestamps but not today's one as it is too late
    assert await historical_portfolio_value_manager.on_new_values(value_by_currency_by_timestamp,
                                                                  save_changes=False) is True
    # also ensure sorting
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [
        friday_timestamp, saturday_timestamp, sunday_timestamp
    ]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            friday_timestamp, friday_value_by_currency)
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[1],
                            saturday_timestamp, saturday_value_by_currency)
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[2],
                            sunday_timestamp, sunday_value_by_currency)

    # now provide an ok timestamp for today's values
    value_by_currency_by_timestamp = {
        friday_timestamp: friday_value_by_currency,     # use exact timestamps for some past timestamps
        sunday_timestamp: sunday_value_by_currency,     # on purpose out of order, value manager is supposed to sort it
        saturday_timestamp + 10: saturday_value_by_currency,
        timestamp: today_value_by_currency,
    }
    assert await historical_portfolio_value_manager.on_new_values(value_by_currency_by_timestamp,
                                                                  save_changes=False) is True
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [
        friday_timestamp, saturday_timestamp, sunday_timestamp, today_timestamp
    ]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[0],
                            friday_timestamp, friday_value_by_currency)
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[1],
                            saturday_timestamp, saturday_value_by_currency)
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[2],
                            sunday_timestamp, sunday_value_by_currency)
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[3],
                            today_timestamp, today_value_by_currency)

    # same call, no new timestamp value
    assert await historical_portfolio_value_manager.on_new_values(value_by_currency_by_timestamp,
                                                                  save_changes=False) is False
    # no major change
    sunday_value_by_currency["USD"] = 3.1
    assert await historical_portfolio_value_manager.on_new_values(value_by_currency_by_timestamp,
                                                                  save_changes=False) is False
    # major change
    sunday_value_by_currency["USD"] = 999
    assert await historical_portfolio_value_manager.on_new_values(value_by_currency_by_timestamp,
                                                                  save_changes=False) is True
    # forced minor change
    sunday_value_by_currency["USD"] = 999.1
    assert await historical_portfolio_value_manager.on_new_values(value_by_currency_by_timestamp,
                                                                  save_changes=False, force_update=True) is True
    assert list(historical_portfolio_value_manager.historical_portfolio_value.keys()) == [
        friday_timestamp, saturday_timestamp, sunday_timestamp, today_timestamp
    ]
    _check_historical_value(list(historical_portfolio_value_manager.historical_portfolio_value.values())[2],
                            sunday_timestamp, sunday_value_by_currency)


async def test_get_historical_value(historical_portfolio_value_manager):
    timestamp = 1648462965  # Monday 28 March 2022 10:22:45 UTC
    exchange_time = timestamp + 10
    friday_timestamp = 1648166400  # Friday 25 March 2022 00:00:00
    saturday_timestamp = 1648252800  # Saturday 26 March 2022 00:00:00
    sunday_timestamp = 1648339200  # Sunday 27 March 2022 00:00:00
    today_timestamp = 1648425600  # Monday 28 March 2022 00:00:00 UTC
    # force exchange current time
    historical_portfolio_value_manager.portfolio_manager.exchange_manager.exchange.connector.backtesting.\
        time_manager.current_timestamp = exchange_time
    friday_value_by_currency = {
        "BTC": 1.1,
        "USD": 3010
    }
    saturday_value_by_currency = {
        "BTC": 1.3
    }
    sunday_value_by_currency = {
        "USD": 3
    }
    today_value_by_currency = {
        "BTC": 11,
        "USD": 54,
        "ETH": 33
    }
    value_by_currency_by_timestamp = {
        friday_timestamp: friday_value_by_currency,     # use exact timestamps for some past timestamps
        sunday_timestamp: sunday_value_by_currency,     # on purpose out of order, value manager is supposed to sort it
        saturday_timestamp + 10: saturday_value_by_currency,
        timestamp: today_value_by_currency,
    }
    await historical_portfolio_value_manager.on_new_values(value_by_currency_by_timestamp, save_changes=False)
    historical_value = historical_portfolio_value_manager.get_historical_value(saturday_timestamp)
    assert historical_value.to_dict() == {
        historical_value.TIMESTAMP_KEY: saturday_timestamp,
        historical_value.VALUES_KEY: saturday_value_by_currency,
    }
    historical_value = historical_portfolio_value_manager.get_historical_value(today_timestamp)
    assert historical_value.to_dict() == {
        historical_value.TIMESTAMP_KEY: today_timestamp,
        historical_value.VALUES_KEY: today_value_by_currency,
    }
    with pytest.raises(KeyError):
        historical_portfolio_value_manager.get_historical_value(1)


async def test_get_historical_values(historical_portfolio_value_manager):
    timestamp = 1648462965  # Monday 28 March 2022 10:22:45 UTC
    exchange_time = timestamp + 10
    friday_timestamp = 1648166400  # Friday 25 March 2022 00:00:00
    saturday_timestamp = 1648252800  # Saturday 26 March 2022 00:00:00
    sunday_timestamp = 1648339200  # Sunday 27 March 2022 00:00:00
    today_timestamp = 1648425600  # Monday 28 March 2022 00:00:00 UTC
    today_hour_timestamp = 1648461600  # Monday 28 March 2022 10:00:00 UTC
    # force exchange current time
    historical_portfolio_value_manager.portfolio_manager.exchange_manager.exchange.connector.backtesting.\
        time_manager.current_timestamp = exchange_time
    historical_portfolio_value_manager.saved_time_frames = [
        commons_enums.TimeFrames.ONE_DAY, commons_enums.TimeFrames.ONE_HOUR
    ]
    friday_value_by_currency = {
        "BTC": 1.1,
        "USD": 3010
    }
    saturday_value_by_currency = {
        "BTC": 1.3
    }
    sunday_value_by_currency = {
        "USD": 3
    }
    today_value_by_currency = {
        "BTC": 11,
        "USD": 54,
        "ETH": 33
    }
    value_by_currency_by_timestamp = {
        friday_timestamp: friday_value_by_currency,     # use exact timestamps for some past timestamps
        sunday_timestamp: sunday_value_by_currency,     # on purpose out of order, value manager is supposed to sort it
        saturday_timestamp + 10: saturday_value_by_currency,
        timestamp: today_value_by_currency,
    }
    historical_portfolio_value_manager.logger = mock.Mock(debug=mock.Mock())
    await historical_portfolio_value_manager.on_new_values(value_by_currency_by_timestamp, save_changes=False)
    assert historical_portfolio_value_manager.get_historical_values("BTC", commons_enums.TimeFrames.ONE_HOUR) == \
        {friday_timestamp: 1.1, saturday_timestamp: 1.3, today_timestamp: 11, today_hour_timestamp: 11}
    # BTC is missing from sunday values
    historical_portfolio_value_manager.logger.debug.assert_called_once()
    historical_portfolio_value_manager.logger.debug.reset_mock()
    assert historical_portfolio_value_manager.get_historical_values("BTC", commons_enums.TimeFrames.ONE_WEEK) == \
        {}
    assert historical_portfolio_value_manager.get_historical_values("USD", commons_enums.TimeFrames.ONE_DAY) == \
        {friday_timestamp: 3010, sunday_timestamp: 3, today_timestamp: 54}
    historical_portfolio_value_manager.logger.debug.assert_called_once()
    historical_portfolio_value_manager.logger.debug.reset_mock()

    late_timestamp = 1648504800  # Monday 28 March 2022 22:00:00 UTC
    late_values = {
        "BTC": 77,
        "USD": 88,
    }
    historical_portfolio_value_manager.portfolio_manager.exchange_manager.exchange.connector.backtesting.\
        time_manager.current_timestamp = late_timestamp
    await historical_portfolio_value_manager.on_new_value(late_timestamp, late_values, save_changes=False)
    assert historical_portfolio_value_manager.get_historical_values("USD", commons_enums.TimeFrames.ONE_DAY) == \
        {
            friday_timestamp: 3010, sunday_timestamp: 3, today_timestamp: 54,
            late_timestamp: 88  # window select include latest value
        }
    historical_portfolio_value_manager.logger.debug.assert_called_once()
    historical_portfolio_value_manager.logger.debug.reset_mock()
    assert historical_portfolio_value_manager.get_historical_values("BTC", commons_enums.TimeFrames.ONE_HOUR) == \
        {friday_timestamp: 1.1, saturday_timestamp: 1.3, today_timestamp: 11, today_hour_timestamp: 11,
         late_timestamp: 77}
    historical_portfolio_value_manager.logger.debug.assert_called_once()
    historical_portfolio_value_manager.logger.debug.reset_mock()
    # with ask timeframe that doesn't round with stored values: adapt select window
    assert historical_portfolio_value_manager.get_historical_values("BTC", commons_enums.TimeFrames.FOUR_HOURS) == \
        {
            friday_timestamp: 1.1, saturday_timestamp: 1.3, today_timestamp: 11, today_hour_timestamp: 11,
            late_timestamp: 77
        }
    historical_portfolio_value_manager.logger.debug.assert_called_once()
    historical_portfolio_value_manager.logger.debug.reset_mock()

    # add 1h missing value to convertable pairs
    convertable_pair = "BTC/USD"
    price = 3000
    historical_portfolio_value_manager.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair[
        convertable_pair] = price
    assert historical_portfolio_value_manager.get_historical_values("BTC", commons_enums.TimeFrames.ONE_HOUR) == \
        {friday_timestamp: 1.1, saturday_timestamp: 1.3, sunday_timestamp: 3 / price,
         today_timestamp: 11, today_hour_timestamp: 11, late_timestamp: 77}
    historical_portfolio_value_manager.logger.debug.assert_not_called()

    # with time select
    assert historical_portfolio_value_manager.get_historical_values(
        "BTC", commons_enums.TimeFrames.ONE_HOUR, from_timestamp=sunday_timestamp, to_timestamp=today_timestamp) == \
        {sunday_timestamp: 3 / price, today_timestamp: 11}
    assert historical_portfolio_value_manager.get_historical_values(
        "BTC", commons_enums.TimeFrames.ONE_HOUR, from_timestamp=sunday_timestamp * 2, to_timestamp=today_timestamp) \
        == {}


def _check_historical_value(historical_value, timestamp, value_by_currency):
    assert isinstance(historical_value, personal_data.HistoricalAssetValue)
    assert historical_value.to_dict() == {
        historical_value.TIMESTAMP_KEY: timestamp,
        historical_value.VALUES_KEY: value_by_currency,
    }
