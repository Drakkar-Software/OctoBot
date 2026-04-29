#  Drakkar-Software OctoBot-Commons
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
import octobot_commons.dict_util as dict_util


def test_find_nested_value():
    assert dict_util.find_nested_value({"a": 1, "b": 2}, "b") == (True, 2)
    assert dict_util.find_nested_value({"a": 1, "b": 2}, "c") == (False, "c")
    assert dict_util.find_nested_value({"a": 1, "b": {"c": 5, "d": "e"}}, "d") == (True, "e")
    assert dict_util.find_nested_value({"a": 1, "b": {"c": 5, "d": {"f": [1, 2, 3]}}}, "f") == (True, [1, 2, 3])
    assert dict_util.find_nested_value({"a": {"e": 7}, "b": {"c": {"t": 5}, "d": {"f": [1, 2, 3], "y": 1}}}, "y") == (True, 1)
    complex_dict = {"a": {"e": 7}, "b": {"c": {"t": [{
        "ab": [8, 9, 10],
        "cd": {
            "4": 4,
            "5": 5,
            "6": [7, 8, 9, {
                "abc": "def",
                "zyx": "zxv"
            }]
        }
    },
        {
            "up": "pa",
            "123": 1234
        }]}, "d": {"f": [1, 2, 3], "y": 1}}}
    assert dict_util.find_nested_value(complex_dict, "abc") == (True, "def")
    assert dict_util.find_nested_value(complex_dict, "5") == (True, 5)
    assert dict_util.find_nested_value(complex_dict, "123") == (True, 1234)


def test_check_and_merge_values_from_reference():
    current_dict = {
        "b": 5,
        "d": 1
    }
    ref_dict = {
        "a": 1,
        "b": 2,
        "c": 3,
        "d": 4
    }
    exception_list = ["d"]
    dict_util.check_and_merge_values_from_reference(current_dict, ref_dict, exception_list)
    assert current_dict == {
        "a": 1,
        "b": 5,
        "c": 3,
        "d": 1
    }


def test_contains_each_element():
    assert dict_util.contains_each_element(
        {},
        {}
    ) is True
    assert dict_util.contains_each_element(
        {},
        {"1": 1}
    ) is False
    assert dict_util.contains_each_element(
        {"1": 1},
        {"1": 1}
    ) is True
    assert dict_util.contains_each_element(
        {"1": 1, "2": 2},
        {"1": 1}
    ) is True
    assert dict_util.contains_each_element(
        {"1": 1},
        {"1": 1, "2": 2}
    ) is False
    assert dict_util.contains_each_element(
        {"1": 1},
        {}
    ) is True
    assert dict_util.contains_each_element(
        {"1": 2},
        {"1": 1}
    ) is False


def test_nested_update_dict():
    assert dict_util.nested_update_dict({}, {"1": 1, "2": 2}) == {"1": 1, "2": 2}
    assert dict_util.nested_update_dict({"1": "aa"}, {"1": 1, "2": 2}) == {"1": 1, "2": 2}
    assert dict_util.nested_update_dict({"1": []}, {"1": 1, "2": 2}) == {"1": 1, "2": 2}
    assert dict_util.nested_update_dict(
        {"1": []}, {"1": 1, "2": 2}, ignore_lists=True
    ) == {"1": [], "2": 2}
    assert dict_util.nested_update_dict(
        {"1": [], "plop": {"jerome": 0, "michel": 1, "monique": [1]}},
        {"1": 1, "2": 2,  "plop": {"jerome": 0.5, "simon": 3, "monique": [2]}},
        ignore_lists=True
    ) == {"1": [], "2": 2, "plop": {"jerome": 0.5, "michel": 1, "monique": [1], "simon": 3}}
    assert dict_util.nested_update_dict(
        {"1": [], "plop": {"jerome": 0, "michel": 1, "monique": [1]}},
        {"1": 1, "2": 2,  "plop": {"jerome": 0.5, "simon": 3, "monique": [2]}},
        ignore_lists=False
    ) == {"1": 1, "2": 2, "plop": {"jerome": 0.5, "michel": 1, "monique": [2], "simon": 3}}
    assert dict_util.nested_update_dict(
        {"1": []},
        {"1": [{"jerome": 0.5, "monique": [2]}, {"simon": 3, "monique": [23]}]},
        ignore_lists=True
    ) == {"1": []}
    assert dict_util.nested_update_dict(
        {"1": []},
        {"1": [{"jerome": 0.5, "monique": [2]}, {"simon": 3, "monique": [23]}]},
        ignore_lists=False
    ) == {'1': [{'jerome': 0.5, 'monique': [2]}, {'monique': [23], 'simon': 3}]}
