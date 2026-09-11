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
import threading

import pytest

import octobot_commons.copy_util as copy_util
import octobot_commons.errors as errors


class TestDeepcopy:
    def test_deepcopies_plain_nested_dict(self):
        source_config = {"metrics": {"count": 1}, "enabled": True}
        copied_config = copy_util.deepcopy(source_config)
        assert copied_config == source_config
        assert copied_config is not source_config
        assert copied_config["metrics"] is not source_config["metrics"]

    def test_raises_copy_error_for_nested_dict_failure(self):
        non_deepcopyable_value = threading.Lock()
        source_config = {"metrics": {"runtime": non_deepcopyable_value}}
        with pytest.raises(errors.CopyError) as raised_error:
            copy_util.deepcopy(source_config, "test context")
        error_message = str(raised_error.value)
        assert "metrics.runtime" in error_message
        assert "lock=" in error_message
        assert "test context" in error_message

    def test_raises_copy_error_for_list_index_path(self):
        non_deepcopyable_value = threading.Lock()
        source_config = {"items": [1, non_deepcopyable_value, 3]}
        with pytest.raises(errors.CopyError) as raised_error:
            copy_util.deepcopy(source_config)
        assert "items[1]" in str(raised_error.value)
        assert "lock=" in str(raised_error.value)

    def test_raises_copy_error_with_root_path_prefix(self):
        non_deepcopyable_value = threading.Lock()
        source_config = {"binance": {"enabled": non_deepcopyable_value}}
        with pytest.raises(errors.CopyError) as raised_error:
            copy_util.deepcopy(
                source_config,
                "profile element",
                "crypto-currencies",
            )
        error_message = str(raised_error.value)
        assert "crypto-currencies.binance.enabled" in error_message
        assert "lock=" in error_message

    def test_chains_original_exception_as_cause(self):
        non_deepcopyable_value = threading.Lock()
        with pytest.raises(errors.CopyError) as raised_error:
            copy_util.deepcopy(non_deepcopyable_value)
        assert isinstance(raised_error.value.__cause__, TypeError)
