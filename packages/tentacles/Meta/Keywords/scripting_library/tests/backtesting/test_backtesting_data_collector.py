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

import octobot_commons.enums as common_enums
import octobot_commons.constants as common_constants

import octobot.constants as constants

import tentacles.Meta.Keywords.scripting_library.backtesting.backtesting_data_collector as src_backtesting_data_collector
import tentacles.Meta.Keywords.scripting_library.errors as errors

class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []
        self.exceptions = []
    def info(self, msg):
        self.infos.append(msg)
    def error(self, msg):
        self.errors.append(msg)
    def exception(self, err, *args, **kwargs):
        self.exceptions.append((err, args, kwargs))

def patch_logger(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(src_backtesting_data_collector, "_get_logger", lambda: logger)
    return logger

def base_args():
    return dict(
        exchange="binance",
        symbol="BTC/USDT",
        time_frame=common_enums.TimeFrames.ONE_HOUR,
        allow_candles_beyond_range=False,
        required_from_the_start=True,
        required_till_the_end=True,
        first_traded_symbols_time=9999999999,  # large for test
        allow_any_backtesting_start_and_end_time=False,
    )


def test_ensure_compatible_candle_time_normal_case(monkeypatch):
    logger = patch_logger(monkeypatch)
    args = base_args()
    tf_sec = common_enums.TimeFramesMinutes[args["time_frame"]] * common_constants.MINUTE_TO_SECONDS
    first_open_time = 1000000
    last_open_time = 1000000 + 10 * tf_sec
    first_candle_time = first_open_time
    last_candle_time = last_open_time
    result = src_backtesting_data_collector.ensure_compatible_candle_time(
        **args,
        first_open_time=first_open_time,
        last_open_time=last_open_time,
        first_candle_time=first_candle_time,
        last_candle_time=last_candle_time,
    )
    assert result is None
    assert not logger.errors
    assert not logger.infos

def test_ensure_compatible_candle_time_starts_too_early():
    args = base_args()
    tf_sec = common_enums.TimeFramesMinutes[args["time_frame"]] * common_constants.MINUTE_TO_SECONDS
    first_open_time = 1000000
    last_open_time = 1000000 + 10 * tf_sec
    first_candle_time = first_open_time - constants.BACKTESTING_DATA_ALLOWED_PRICE_WINDOW - 1
    last_candle_time = last_open_time
    with pytest.raises(errors.InvalidBacktestingDataError) as exc:
        src_backtesting_data_collector.ensure_compatible_candle_time(
            **args,
            first_open_time=first_open_time,
            last_open_time=last_open_time,
            first_candle_time=first_candle_time,
            last_candle_time=last_candle_time,
        )
    assert "starts too early" in str(exc.value)

def test_ensure_compatible_candle_time_starts_too_late_and_required():
    args = base_args()
    tf_sec = common_enums.TimeFramesMinutes[args["time_frame"]] * common_constants.MINUTE_TO_SECONDS
    first_open_time = 1000000
    last_open_time = 1000000 + 10 * tf_sec
    first_candle_time = first_open_time + tf_sec * 2
    last_candle_time = last_open_time
    args["first_traded_symbols_time"] = first_open_time - constants.BACKTESTING_DATA_ALLOWED_PRICE_WINDOW  # force fail
    with pytest.raises(errors.InvalidBacktestingDataError) as exc:
        src_backtesting_data_collector.ensure_compatible_candle_time(
            **args,
            first_open_time=first_open_time,
            last_open_time=last_open_time,
            first_candle_time=first_candle_time,
            last_candle_time=last_candle_time,
        )
    assert "starts too late" in str(exc.value)

def test_ensure_compatible_candle_time_starts_too_late_but_adapted_with_test_data(monkeypatch):
    logger = patch_logger(monkeypatch)
    args = base_args()
    tf_sec = common_enums.TimeFramesMinutes[args["time_frame"]] * common_constants.MINUTE_TO_SECONDS
    first_open_time = 1000000
    last_open_time = 1000000 + 10 * tf_sec
    first_candle_time = first_open_time + tf_sec * 2
    last_candle_time = last_open_time
    args["first_traded_symbols_time"] = first_open_time + tf_sec * 3  # allow adaptation
    result = src_backtesting_data_collector.ensure_compatible_candle_time(
        **args,
        first_open_time=first_open_time,
        last_open_time=last_open_time,
        first_candle_time=first_candle_time,
        last_candle_time=last_candle_time,
    )
    assert result == first_candle_time
    assert any("acceptable, start time is adapted" in msg for msg in logger.infos)

def test_ensure_compatible_candle_time_starts_too_late_but_adapted_with_real_data_dca(monkeypatch):
    logger = patch_logger(monkeypatch)
    args = base_args()
    args["time_frame"] = common_enums.TimeFrames.FOUR_HOURS
    first_open_time = 1737424774.2265518 # Tuesday, January 21, 2025 9:44:54.459
    last_open_time = 1752990294.4590356 # Sunday, July 20, 2025 5:44:54.459
    first_candle_time = 1737446400  # Tuesday, January 21, 2025 12:00:00
    last_candle_time = 1752955200 # Saturday, July 19, 2025 20:00:00
    args["first_traded_symbols_time"] = 1737465882.5380511  # Tuesday, January 21, 2025 13:24:42.538
    # fails without the kw_constants.BACKTESTING_DATA_ALLOWED_PRICE_WINDOW allowance over first_traded_symbols_time
    result = src_backtesting_data_collector.ensure_compatible_candle_time(
        **args,
        first_open_time=first_open_time,
        last_open_time=last_open_time,
        first_candle_time=first_candle_time,
        last_candle_time=last_candle_time,
    )
    assert result == first_candle_time
    assert any("acceptable, start time is adapted" in msg for msg in logger.infos)
    
    first_candle_time = args["first_traded_symbols_time"] + constants.BACKTESTING_DATA_ALLOWED_PRICE_WINDOW  # Thursday, January 23, 2025 13:24:42.538
    with pytest.raises(errors.InvalidBacktestingDataError) as exc:
      result = src_backtesting_data_collector.ensure_compatible_candle_time(
          **args,
          first_open_time=first_open_time,
          last_open_time=last_open_time,
          first_candle_time=first_candle_time,
          last_candle_time=last_candle_time,
      )
    assert "starts too late" in str(exc.value)

def test_ensure_compatible_candle_time_starts_too_late_but_adapted_with_real_data_basked(monkeypatch):
    logger = patch_logger(monkeypatch)
    args = base_args()
    args["time_frame"] = common_enums.TimeFrames.FOUR_HOURS
    first_open_time = 1737453626.6562696 # Tuesday, January 21, 2025 10:00:26.656
    last_open_time = 1752919226.658268 # Saturday, July 19, 2025 10:00:26.658
    first_candle_time = 1737590400  # Thursday, January 23, 2025 0:00:00
    last_candle_time = 1752883200 # Saturday, July 19, 2025 0:00:00
    args["first_traded_symbols_time"] = 1749325565.048149  # Saturday, June 7, 2025 19:46:05.048
    result = src_backtesting_data_collector.ensure_compatible_candle_time(
        **args,
        first_open_time=first_open_time,
        last_open_time=last_open_time,
        first_candle_time=first_candle_time,
        last_candle_time=last_candle_time,
    )
    assert result == first_candle_time
    assert any("acceptable, start time is adapted" in msg for msg in logger.infos)

def test_ensure_compatible_candle_time_ends_too_late():
    args = base_args()
    tf_sec = common_enums.TimeFramesMinutes[args["time_frame"]] * common_constants.MINUTE_TO_SECONDS
    first_open_time = 1000000
    last_open_time = 1000000 + 10 * tf_sec
    first_candle_time = first_open_time
    last_candle_time = last_open_time + tf_sec * 2
    with pytest.raises(errors.InvalidBacktestingDataError) as exc:
        src_backtesting_data_collector.ensure_compatible_candle_time(
            **args,
            first_open_time=first_open_time,
            last_open_time=last_open_time,
            first_candle_time=first_candle_time,
            last_candle_time=last_candle_time,
        )
    assert "ends too late" in str(exc.value)

def test_ensure_compatible_candle_time_ends_too_early_and_required():
    args = base_args()
    tf_sec = common_enums.TimeFramesMinutes[args["time_frame"]] * common_constants.MINUTE_TO_SECONDS
    first_open_time = 1000000
    last_open_time = 1000000 + 10 * tf_sec
    first_candle_time = first_open_time
    last_candle_time = last_open_time - constants.BACKTESTING_DATA_ALLOWED_PRICE_WINDOW - 1
    with pytest.raises(errors.InvalidBacktestingDataError) as exc:
        src_backtesting_data_collector.ensure_compatible_candle_time(
            **args,
            first_open_time=first_open_time,
            last_open_time=last_open_time,
            first_candle_time=first_candle_time,
            last_candle_time=last_candle_time,
        )
    assert "ends too early" in str(exc.value)

def test_ensure_compatible_candle_time_ends_too_early_but_not_required(monkeypatch):
    logger = patch_logger(monkeypatch)
    args = base_args()
    args["required_till_the_end"] = False
    first_open_time = 1000000
    last_open_time = 1000000 + constants.BACKTESTING_DATA_ALLOWED_PRICE_WINDOW
    first_candle_time = first_open_time
    last_candle_time = last_open_time - constants.BACKTESTING_DATA_ALLOWED_PRICE_WINDOW  - 1
    result = src_backtesting_data_collector.ensure_compatible_candle_time(
        **args,
        first_open_time=first_open_time,
        last_open_time=last_open_time,
        first_candle_time=first_candle_time,
        last_candle_time=last_candle_time,
    )
    assert result is None
    assert any("acceptable, this symbol is not required till the end" in msg for msg in logger.infos)

def test_ensure_compatible_candle_time_adapted_start_time_too_short():
    args = base_args()
    tf_sec = common_enums.TimeFramesMinutes[args["time_frame"]] * common_constants.MINUTE_TO_SECONDS
    first_open_time = 1000000
    last_open_time = 1000000 + 30 * tf_sec
    first_candle_time = first_open_time + 25 * tf_sec
    last_candle_time = last_open_time
    args["first_traded_symbols_time"] = first_open_time + 30 * tf_sec
    # This will adapt, but duration will be too short
    with pytest.raises(errors.InvalidBacktestingDataError) as exc:
        src_backtesting_data_collector.ensure_compatible_candle_time(
            **args,
            first_open_time=first_open_time,
            last_open_time=last_open_time,
            first_candle_time=first_candle_time,
            last_candle_time=last_candle_time,
        )
    assert "adapted backtesting start time starts too late" in str(exc.value)



