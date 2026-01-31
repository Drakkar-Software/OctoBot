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
import pytest
import octobot_commons.constants as constants
import octobot_commons.configuration as configuration


class TestHistoricalConfiguration:
    """Test class for historical configuration functions"""

    def setup_method(self):
        """Set up test fixtures"""
        self.empty_master_config = {}
        self.master_config_with_historical = {} 
        for ts, config in (
          [1000.0, {"param1": "value1", "param2": "value2"}],
          [2000.0, {"param1": "value3", "param2": "value4"}],
          [3000.0, {"param1": "value5", "param2": "value6"}],
        ):
          # add config using add_historical_tentacle_config to maintain order
          configuration.add_historical_tentacle_config(self.master_config_with_historical, ts, config)
        
        self.test_config = {"test_param": "test_value"}
        self.test_start_time = 1500.0

    def test_add_historical_tentacle_config_empty_master_config(self):
        assert constants.CONFIG_HISTORICAL_CONFIGURATION not in self.empty_master_config
        """Test adding historical config to empty master config"""
        configuration.add_historical_tentacle_config(
            self.empty_master_config, self.test_start_time, self.test_config
        )
        
        assert constants.CONFIG_HISTORICAL_CONFIGURATION in self.empty_master_config
        assert len(self.empty_master_config[constants.CONFIG_HISTORICAL_CONFIGURATION]) == 1
        assert self.empty_master_config[constants.CONFIG_HISTORICAL_CONFIGURATION][0] == [
            self.test_start_time, self.test_config
        ]

    def test_add_historical_tentacle_config_existing_master_config(self):
        """Test adding historical config to existing master config"""
        original_length = len(self.master_config_with_historical[constants.CONFIG_HISTORICAL_CONFIGURATION])
        
        configuration.add_historical_tentacle_config(
            self.master_config_with_historical, self.test_start_time, self.test_config
        )
        
        # Check that the new config was added
        assert len(self.master_config_with_historical[constants.CONFIG_HISTORICAL_CONFIGURATION]) == original_length + 1
        
        # Check that the list is sorted by timestamp in descending order (most recent first)
        timestamps = [config[0] for config in self.master_config_with_historical[constants.CONFIG_HISTORICAL_CONFIGURATION]]
        assert timestamps == sorted(timestamps, reverse=True)
        
        # Check that our new config is in the list
        config_found = False
        for config in self.master_config_with_historical[constants.CONFIG_HISTORICAL_CONFIGURATION]:
            if config[0] == self.test_start_time and config[1] == self.test_config:
                config_found = True
                break
        assert config_found

    def test_add_historical_tentacle_config_multiple_additions(self):
        """Test adding multiple historical configs maintains sorting"""
        configuration.add_historical_tentacle_config(self.empty_master_config, 1000.0, {"config": "old"})
        configuration.add_historical_tentacle_config(self.empty_master_config, 3000.0, {"config": "new"})
        configuration.add_historical_tentacle_config(self.empty_master_config, 2000.0, {"config": "middle"})
        
        timestamps = [config[0] for config in self.empty_master_config[constants.CONFIG_HISTORICAL_CONFIGURATION]]
        assert timestamps == [3000.0, 2000.0, 1000.0]

    def test_has_any_historical_tentacle_config_empty(self):
        """Test has_any_historical_tentacle_config with empty config"""
        assert not configuration.has_any_historical_tentacle_config(self.empty_master_config)

    def test_has_any_historical_tentacle_config_with_historical(self):
        """Test has_any_historical_tentacle_config with existing historical config"""
        assert configuration.has_any_historical_tentacle_config(self.master_config_with_historical)

    def test_has_any_historical_tentacle_config_other_keys(self):
        """Test has_any_historical_tentacle_config with other keys but not historical"""
        config_with_other_keys = {"other_key": "value", "another_key": "value2"}
        assert not configuration.has_any_historical_tentacle_config(config_with_other_keys)

    def test_get_historical_tentacle_config_exact_match(self):
        """Test getting historical config with exact time match"""
        result = configuration.get_historical_tentacle_config(self.master_config_with_historical, 2000.0)
        assert result == {"param1": "value3", "param2": "value4"}

    def test_get_historical_tentacle_config_between_times(self):
        """Test getting historical config with time between existing configs"""
        result = configuration.get_historical_tentacle_config(self.master_config_with_historical, 1500.0)
        assert result == {"param1": "value1", "param2": "value2"}

    def test_get_historical_tentacle_config_before_oldest(self):
        """Test getting historical config with time before oldest config"""
        result = configuration.get_historical_tentacle_config(self.master_config_with_historical, 500.0)
        # Should return the oldest config (last in the list)
        assert result == {"param1": "value1", "param2": "value2"}

    def test_get_historical_tentacle_config_after_newest(self):
        """Test getting historical config with time after newest config"""
        result = configuration.get_historical_tentacle_config(self.master_config_with_historical, 4000.0)
        # Should return the newest config (first in the list)
        assert result == {"param1": "value5", "param2": "value6"}

    def test_get_historical_tentacle_config_key_error(self):
        """Test get_historical_tentacle_config raises KeyError when key not found"""
        with pytest.raises(KeyError) as exc_info:
            configuration.get_historical_tentacle_config(self.empty_master_config, 1000.0)
        assert constants.CONFIG_HISTORICAL_CONFIGURATION in str(exc_info.value)

    def test_get_historical_tentacle_configs_empty_interval(self):
        """Test getting historical configs with empty time interval"""
        result = configuration.get_historical_tentacle_configs(self.master_config_with_historical, 5000.0, 6000.0)
        assert result == []

    def test_get_historical_tentacle_configs_full_interval(self):
        """Test getting historical configs with full time interval"""
        result = configuration.get_historical_tentacle_configs(self.master_config_with_historical, 500.0, 4000.0)
        assert len(result) == 3
        # Should be ordered by most recent first
        assert result[0] == {"param1": "value5", "param2": "value6"}
        assert result[1] == {"param1": "value3", "param2": "value4"}
        assert result[2] == {"param1": "value1", "param2": "value2"}

    def test_get_historical_tentacle_configs_partial_interval(self):
        """Test getting historical configs with partial time interval"""
        result = configuration.get_historical_tentacle_configs(self.master_config_with_historical, 1500.0, 2500.0)
        assert len(result) == 1
        assert result[0] == {"param1": "value3", "param2": "value4"}

    def test_get_historical_tentacle_configs_exact_boundaries(self):
        """Test getting historical configs with exact boundary times"""
        result = configuration.get_historical_tentacle_configs(self.master_config_with_historical, 1000.0, 3000.0)
        assert len(result) == 3

    def test_get_historical_tentacle_configs_key_error(self):
        """Test get_historical_tentacle_configs raises KeyError when key not found"""
        with pytest.raises(KeyError) as exc_info:
            configuration.get_historical_tentacle_configs(self.empty_master_config, 1000.0, 2000.0)
        assert constants.CONFIG_HISTORICAL_CONFIGURATION in str(exc_info.value)

    def test_get_oldest_historical_tentacle_config_time_success(self):
        """Test getting oldest historical config time successfully"""
        result = configuration.get_oldest_historical_tentacle_config_time(self.master_config_with_historical)
        assert result == 1000.0

    def test_get_oldest_historical_tentacle_config_time_empty_list(self):
        """Test getting oldest historical config time with empty list"""
        config_with_empty_list = {constants.CONFIG_HISTORICAL_CONFIGURATION: []}
        with pytest.raises(ValueError) as exc_info:
            configuration.get_oldest_historical_tentacle_config_time(config_with_empty_list)
        assert "No historical configuration found" in str(exc_info.value)

    def test_get_oldest_historical_tentacle_config_time_missing_key(self):
        """Test getting oldest historical config time with missing key"""
        # Should return the minimum of an empty list, which raises ValueError
        with pytest.raises(ValueError) as exc_info:
            configuration.get_oldest_historical_tentacle_config_time(self.empty_master_config)
        assert "No historical configuration found" in str(exc_info.value)

    def test_get_oldest_historical_tentacle_config_time_single_config(self):
        """Test getting oldest historical config time with single config"""
        single_config = {
            constants.CONFIG_HISTORICAL_CONFIGURATION: [[1500.0, {"test": "config"}]]
        }
        result = configuration.get_oldest_historical_tentacle_config_time(single_config)
        assert result == 1500.0

    def test_integration_scenario(self):
        """Test integration scenario with multiple operations"""
        # Start with empty config
        master_config = {}
        
        # Add multiple configs
        configuration.add_historical_tentacle_config(master_config, 1000.0, {"version": "1.0"})
        configuration.add_historical_tentacle_config(master_config, 2000.0, {"version": "2.0"})
        configuration.add_historical_tentacle_config(master_config, 1500.0, {"version": "1.5"})
        
        # Check that historical config exists
        assert configuration.has_any_historical_tentacle_config(master_config)
        
        # Get config for different times
        assert configuration.get_historical_tentacle_config(master_config, 500.0) == {"version": "1.0"}
        assert configuration.get_historical_tentacle_config(master_config, 1200.0) == {"version": "1.0"}
        assert configuration.get_historical_tentacle_config(master_config, 1600.0) == {"version": "1.5"}
        assert configuration.get_historical_tentacle_config(master_config, 2500.0) == {"version": "2.0"}
        
        # Get configs for time intervals
        configs_1000_2000 = configuration.get_historical_tentacle_configs(master_config, 1000.0, 2000.0)
        assert len(configs_1000_2000) == 3
        
        # Get oldest time
        assert configuration.get_oldest_historical_tentacle_config_time(master_config) == 1000.0
