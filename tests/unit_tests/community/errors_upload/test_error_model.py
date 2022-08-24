#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import copy

from tests.unit_tests.community.errors_upload import basic_error, exception_error, ERROR_TITLE, ERROR_METRICS_ID, \
    ERROR_TIME


def test_constructor_with_basic_error(basic_error):
    assert basic_error.error is None
    assert basic_error.title is ERROR_TITLE
    assert basic_error.first_timestamp == ERROR_TIME
    assert basic_error.last_timestamp == ERROR_TIME
    assert basic_error.count == 1
    assert basic_error.metrics_id is ERROR_METRICS_ID
    assert basic_error.type == ""
    assert basic_error.stacktrace == []


def test_constructor_with_exception_error(exception_error):
    assert isinstance(exception_error.error, ZeroDivisionError)
    assert exception_error.title is ERROR_TITLE
    assert exception_error.first_timestamp == ERROR_TIME
    assert exception_error.last_timestamp == ERROR_TIME
    assert exception_error.count == 1
    assert exception_error.metrics_id is ERROR_METRICS_ID
    assert exception_error.type == ZeroDivisionError.__name__
    assert len(exception_error.stacktrace) == 5


def test_to_dict(exception_error):
    dict_repr = exception_error.to_dict()
    assert len(dict_repr) == 7
    assert all(bool(v) for v in dict_repr.values())


def test_is_equivalent(basic_error, exception_error):
    assert not basic_error.is_equivalent(exception_error)
    assert not exception_error.is_equivalent(basic_error)
    assert exception_error.is_equivalent(exception_error)
    assert basic_error.is_equivalent(basic_error)

    exception_error2 = copy.deepcopy(exception_error)
    basic_error2 = copy.deepcopy(basic_error)

    exception_error2.count += 1
    assert exception_error.is_equivalent(exception_error2)
    exception_error2.title += "1"
    assert not exception_error.is_equivalent(exception_error2)

    basic_error2.type = NotImplementedError
    assert not basic_error.is_equivalent(basic_error2)


def test_merge_equivalent(basic_error, exception_error):
    exception_error.last_timestamp = ERROR_TIME + 1
    basic_error.merge_equivalent(exception_error)
    assert basic_error.first_timestamp == ERROR_TIME
    assert basic_error.last_timestamp == ERROR_TIME + 1
    assert basic_error.count == 2
    exception_error.merge_equivalent(basic_error)
    assert exception_error.first_timestamp == ERROR_TIME
    assert exception_error.last_timestamp == ERROR_TIME + 1
    assert exception_error.count == 3
