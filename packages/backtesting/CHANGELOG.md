# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.10.0] - 2026-01-04
### Updated 
[Requirements] Bump OctoBot-Commons version

## [1.9.8] - 2025-11-26
### Added 
[Requirements] [full] requirements installation

## [1.9.7] - 2023-12-11
### Added
- [Backtesting] extra_backtesting_time_frames

## [1.9.6] - 2023-12-06
### Added
- [BacktestData] use_cached_markets

## [1.9.5] - 2023-10-27
### Added
- [API] adapt_backtesting_channels return value

## [1.9.4] - 2023-10-15
### Updated
- [Timeframes] allow accurate price time frame

## [1.9.2] - 2023-09-03
### Updated
- [Timeframes] allow minimal available timeframe instead of forcing 1m
- [TimeChannel] rename to avoid conflicts

## [1.9.1] - 2023-08-14
### Added
- [BacktestData] forced_markets

## [1.9.0] - 2023-05-02
### Updated
- Supported python versions
### Removed
- Cython

## [1.8.2] - 2022-04-21
### Updated
- [ExchangeCollector] handle exchange credentials

## [1.8.1] - 2022-04-17
### Updated
- [ExchangeCollector] delete_all

## [1.8.0] - 2022-12-23
### Updated
- [ChannelsManager] drop unused producers and priority levels
- cython version

## [1.7.5] - 2022-10-13
### Updated
- [ExchangeCollector] Cython header

## [1.7.4] - 2022-10-12
### Updated
- [Symbols] Use unified symbols

## [1.7.3] - 2022-08-24
### Updated
- [Cache] Optimize cache init

## [1.7.2] - 2022-06-05
### Updated
- [Symbols] Update for symbol object

## [1.7.1] - 2022-05-02
### Added
- [API] get_data_file_from_importers

## [1.7.0] - 2022-03-31
### Updated
- [DataImporter] optimized backtesting historical data reading
- [Databases] migrate databases into octobot-commons

## [1.6.29] - 2022-01-16
### Updated
- synchronized_perform_consumers_queue call

## [1.6.28] - 2022-01-08
### Updated
- Bump requirements

## [1.6.27] - 2021-11-18
### Updated
- aiohttp requirement

## [1.6.26] - 2021-10-07
### Updated
- BacktestingApi add start and end timestamp to adapt_backtesting_channels

## [1.6.25] - 2021-09-22
### Added
- BacktestingApi add stop_data_collector

## [1.6.24] - 2021-09-19
### Updated
- bump requirements

## [1.6.23] - 2021-09-10
### Fixed
- Data collector attributes visibility

## [1.6.22] - 2021-09-07
### Updated
- Data collector variables names

## [1.6.21] - 2021-09-06
### Updated
- BacktestingApi Add initialize_and_run_data_collector
- BacktestingApi Add is_data_collector_in_progress
- BacktestingApi Add get_data_collector_progress
- BacktestingApi Add is_data_collector_finished
- ExchangeDataCollector Add progression info
- DataCollector Add collection status (started, finished)

## [1.6.20] - 2021-07-19
### Updated
- bump requirements

## [1.6.19] - 2021-07-04
### Fixed
- ExchangeDataCollector cython typing

## [1.6.18] - 2021-07-04
### Updated
- ExchangeDataCollector add start and end timestamp for collecting data

## [1.6.17] - 2021-05-05
### Updated
- bump requirements

## [1.6.16] - 2021-03-19 
### Added 
- Timestamp to data_file description

## [1.6.15] - 2021-03-06 
### Updated 
- Force chardet version

## [1.6.14] - 2021-03-03 
### Added 
- Python 3.9 support

## [1.6.13] - 2020-02-25
### Updated
- Requirements

## [1.6.12] - 2020-02-03
### Added
- Default importer handling

## [1.6.11] - 2020-12-28
### Updated
- Requirements

## [1.6.10] - 2020-12-23
### Updated
- Requirements

## [1.6.9] - 2020-12-09
### Updated
- Use OctoBot commons configuration keys

## [1.6.8] - 2020-11-22
### Fixed
- Exchange collector tentacles_setup_config visibility

## [1.6.7] - 2020-11-21
### Updated
- OctoBot-Trading import

## [1.6.6] - 2020-11-14
### Updated
- Enable tentacles exchanges usage in data collector

## [1.6.5] - 2020-11-07
### Updated
- Requirements

## [1.6.4] - 2020-10-30
### Updated
- Concurrent database cursor management

## [1.6.3] - 2020-10-29
### Updated
- Commons requirement

## [1.6.2] - 2020-10-24
### Updated
- Aiohttp requirement

## [1.6.1] - 2020-10-23
### Updated
- Python 3.8 support

## [1.6.0] - 2020-10-18
### Changed
- Imports

### Updated
- Aiohttp requirement

## [1.5.20] - 2020-09-01
### Updated
- Requirements

## [1.5.19] - 2020-08-15
### Updated
- Requirements

## [1.5.18] - 2020-06-28
### Updated
- Requirements

## [1.5.17] - 2020-06-19
### Updated
- Requirements

## [1.5.16] - 2020-06-05
### Fixed
- Async concurrency issue on backtesting stop

## [1.5.15] - 2020-05-30
### Updated
- Clear connection database attribute on stop

## [1.5.14] - 2020-05-27
### Updated
- Cython version

## [1.5.13] - 2020-05-21
### Updated
- Remove advanced manager from commons

## [1.5.12] - 2020-05-17
### Fixed
- [DataFiles] Cython header

## [1.5.11] - 2020-05-16
### Fixed
- [ExchangeCollector] Cython header

## [1.5.10] - 2020-05-16
### Updated
- Requirements

## [1.5.9] - 2020-05-14
### Changed
- [Database] Fix async concurrent access issues

## [1.5.8] - 2020-05-14
### Changed
- [ChannelsManager] Iterates on ChannelConsumerPriorityLevels

## [1.5.7] - 2020-05-12
### Fixed
- Date description parsing

## [1.5.6] - 2020-05-11
### Added
- Multiple data files support

## [1.5.5] - 2020-05-10
### Added
- Backtesting duration API

## [1.5.4] - 2020-05-10
### Fixed
- Backtesting progress management

## [1.5.3] - 2020-05-09
### Updated
- Channels requirement

## [1.5.2] - 2020-05-08
### Fixed
- Time manager memory leaks

## [1.5.1] - 2020-05-05
### Fixed
- Timestamp list generation

## [1.5.0] - 2020-05-02
### Added
- Synchronized backtesting

## [1.4.1] - 2020-05-02
### Updated
- octobot-channels requirements

## [1.4.0] - 2020-05-02
### Updated
- Migrate octobot-backtesting, indepdendent-backtesting and strategy-optimizer into OctoBot repository
- backtesting and importer API

## [1.3.20] - 2020-04-29
### Fixed
- Time channel non-existing attribute set

## [1.3.19] - 2020-04-28
### Updated
- Cython header files

## [1.3.18] - 2020-04-18
### Updated
- Time management and debug logs

## [1.3.17] - 2020-04-18
### Updated
- Cython header files

## [1.3.16] - 2020-04-18
### Added
- Handle backtesting errors

### Updated
- Use updated evaluator matrix API
- Do not crash on backtesting missing files

## [1.3.15] - 2020-04-10
### Added
- Service feeds handling

## [1.3.14] - 2020-04-07
### Fixed
- Wildcard imports

## [1.3.13] - 2020-04-05
### Updated
- Integrate OctoBot-tentacles-manager 2.0.0

## [1.3.12] - 2020-03-30
### Updated
**Requirements**
- Commons version to 1.3.5
- Cython version to 0.29.16
- Channels version to 1.3.22

## [1.3.11] - 2020-03-07
### Updated
**Requirements**
- Commons version to 1.3.0
- CCXT version to 1.23.67

## [1.3.10] - 2020-02-18
### Fixed
- Remove hard octobot_evaluators import

## [1.3.9] - 2020-02-17
### Added
- Backtesting finished event

### Updated
- Data converters
- Backtesting API
- DataFile converter API
- Database error handling
- IndependentBacktesting flexibily for strategy optimizer

### Fixed
- Compiled double accuracy

## [1.3.8] - 2020-02-06
### Added
- Independent backtesting handling

### Updated
- Backtesting API
- Importer API
- DataFile API

## [1.3.7] - 2020-02-02
### Updated
- Backtesting API
- Importer API

## [1.3.6] - 2020-01-26
### Updated
- Backtesting API
- Backtesting workflow

## [1.3.5] - 2020-01-23
### Updated
- Backtesting API

## [1.3.4] - 2020-01-18
### Added
- AbstractExchangeHistoryCollector and AbstractExchangeLiveCollector

### Updated
- Data collector to work from web interface
- collect_exchange_historical_data and get_file_description APIs

## [1.3.3] - 2020-01-02
### Added
- Backtesting, data_file and exchange_data_collector API
- is_in_progress method in Backtesting
- use_all_available_timeframes in exchange collector

### Updated
- data_file_manager imports
- Commons version to 1.2.1

## [1.3.2] - 2019-12-21
### Updated
**Requirements**
- Commons version to 1.2.0
- Channels version to 1.3.6

## [1.3.1] - 2019-12-14
### Updated
**Requirements**
- Commons version to 1.1.51
- Channels version to 1.3.6
- aiosqlite version to 0.11.0

## [1.3.0] - 2019-11-07
## Added
- Timestamp interval management (starting and stopping)

### Fixed
- Database select where clauses generation

## [1.2.5] - 2019-10-30
## Added
- OSX support

## [1.2.4] - 2019-10-09
## Added
- PyPi manylinux deployment

## [1.2.3] - 2019-10-08
### Changed
- Constants VERSION and PROJECT_NAME file location 

## [1.2.2] - 2019-10-08
## Fixed
- Install with setup

## [1.2.1] - 2019-10-07
### Added
- Collector async http with aiohttp

### Changed
- Improved database management

## [1.2.0] - 2019-10-05
### Added
- Converters classes
- Database indexes
- Tentacles management (Importers, Collectors, Converters)
- Database async management

### Changed
- Fully async backtesting

## [1.1.1] - 2019-09-18
### Added
- Time management from OctoBot-Trading

## [1.1.0] - 2019-09-16
### Added
- Collectors basis
- Importers basis
- Exchange collectors (Live and History)
- Exchange importer
- Database manager

## [1.0.0] - 2019-09-10
### Added
- Package components from OctoBot project
