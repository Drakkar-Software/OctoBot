# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.10.6] - 2026-01-23
### Fixed 
[BaseTreeNode] Fix missing description and metadata in path functions

## [1.10.5] - 2026-01-23
### Added 
[BaseTreeNode] add description and metadata

## [1.10.4] - 2026-01-21
### Added 
- "markets" to InitializationEventExchangeTopics

## [1.10.3] - 2026-01-11
### Added 
- [ContextUtil] add EmptyContextManager
### Updated
- [ProfileData] make ProfileData an UpdatableDataclass

## [1.10.2] - 2026-01-07
### Added 
- RSA, AES and ECDSA encryption functions

## [1.10.1] - 2026-01-03
### Added 
- CONFIG_EXCHANGE_OPTION constant
- `is_symbol` to symbol_util

## [1.10.0] - 2026-01-02
### Added 
- Option symbols supports in Symbol operations (Warning: `market_separator` is not the fourth param of `merge_currencies` anymore, it shouldn't be a breaking change as it should be called with kwargs)

## [1.9.92] - 2025-12-16
### Added 
[DSL] add operator docs

## [1.9.91] - 2025-12-05
### Added 
[AsyncTools] add gather_waiting_for_all_before_raising

## [1.9.90] - 2025-12-03
### Updated 
[Cache] reduce symbol util cache to free RAM

## [1.9.89] - 2025-12-02
### Added 
[OS] Add is_raspberry_pi_machine()

## [1.9.88] - 2025-11-26
### Added 
[Requirements] fix full requirements installation

## [1.9.87] - 2025-11-26
### Added 
[Requirements] [full] requirements

## [1.9.86] - 2025-11-18
### Fixed 
[Constants] usd-like coins list

## [1.9.85] - 2025-11-18
### Added 
[DSL] add DSL interpreter

## [1.9.84] - 2025-11-07
### Added 
[Constants] add CONFIG_FORCE_AUTHENTICATION

## [1.9.83] - 2025-10-17
### Added 
[Constants] add DEFAULT_REFERENCE_MARKET

## [1.9.82] - 2025-08-24
### Added 
[Signals] add dependencies

## [1.9.81] - 2025-08-16
### Added 
[ProfileData] add exchange_account_id

## [1.9.80] - 2025-07-17
### Updated 
[Time] fix timezone deprecation

## [1.9.79] - 2025-07-12
### Added 
[HistoricalConfig] add checker and multi config selector

## [1.9.78] - 2025-06-16
### Added 
[Authentication] add kwargs to update_portfolio

## [1.9.77] - 2025-05-31
### Added 
[DisplayTranslator] temporary fix field dependency issue

## [1.9.76] - 2025-05-23
### Added 
[ProfileData] add nested_strategy_config_id
[ListUtil] deduplicate

## [1.9.75] - 2025-05-21
### Added 
[Constants] add distribution

## [1.9.74] - 2025-03-18
### Updated 
[ProfileData] add sub portfolio requirements

## [1.9.73] - 2025-02-23
### Updated 
[DictUtil] add ignore_lists

## [1.9.72] - 2025-02-16
### Fixed
[ProfileData] fix future_exchange_data default value

## [1.9.71] - 2025-02-10
### Added
[Constants] add TRADING_SYMBOL_REGEX

## [1.9.70] - 2024-12-11
### Added
[Constants] add FIAT_NON_USD_LIKE_COINS

## [1.9.69] - 2024-12-06
### Added
[ProfileData] remove proxy_id

## [1.9.68] - 2023-12-03
### Added
[Authenticator] update positions
[ProfileData] leverage and exchange_type

## [1.9.67] - 2023-12-02
### Updated
[HTML] handle html exception args

## [1.9.66] - 2023-12-02
### Updated
[HTML] handle nested exception causes

## [1.9.65] - 2023-11-24
### Added
[Configuration] add get_oldest_historical_tentacle_config_time
[AbstractTentacle] add get_tentacle_config_traded_symbols

## [1.9.64] - 2023-11-23
### Added
[Tentacles] historical config

## [1.9.63] - 2023-11-21
### Added
[html] add html summarizer

## [1.9.62] - 2023-11-11
### Added
[aiohttp] add CounterClientSession

## [1.9.61] - 2023-10-23
### Added
[ProfileData] add proxy_id
[Constants] add CONFIG_EXCHANGE_ACCESS_TOKEN

## [1.9.60] - 2023-10-12
### Added
[ProfileData] add exchange_id

## [1.9.59] - 2023-10-03
### Added
[CommunityChannelTypes] add CONFIGURATION

## [1.9.58] - 2023-08-28
### Updated
[ExchangeAuthData] add exchange config when missing

## [1.9.57] - 2023-08-28
### Added
ExchangeAuthData
### Updated
[ExchangeAuthData] add exchange_type and sandboxed

## [1.9.56] - 2023-08-28
### Added
ExchangeAuthData
### Updated
[ProfileImport] add force_simulator param

## [1.9.55] - 2023-08-25
### Updated
[Config] remove custom restore file
[Config] allow restore file copy failure

## [1.9.54] - 2023-08-21
### Updated
[Authenticator] update update_orders args 
## [1.9.53] - 2023-08-19
### Added
[Constants] CONFIG_EXCHANGE_UID

## [1.9.52] - 2023-08-18
### Added
[ProfileData] TentaclesProfileDataTranslator

## [1.9.51] - 2023-07-23
### Added
[Authenticator] wait_and_check_has_open_source_package

## [1.9.50] - 2023-07-15
### Added
[OS] optional RAM watcher

## [1.9.49] - 2023-07-04
### Added
[Profiles] handle registered tentacles in import

## [1.9.48] - 2023-07-03
### Added
[Profiles] handle profile update

## [1.9.47] - 2023-06-12
### Added
[CommunityChannelTypes] add TRADINGVIEW

## [1.9.46] - 2023-05-26
### Updated
ProfileData: added enable field on traded pairs

## [1.9.45] - 2023-04-21
### Added
certify_aiohttp_client_session

## [1.9.44] - 2023-04-18
### Added
ssl_fallback_aiohttp_client_session

## [1.9.43] - 2023-03-21
### Added
PROFITABILITY to InitializationEventExchangeTopics

## [1.9.42] - 2023-02-20
### Removed
- usd_like_value from MinimalFund

## [1.9.41] - 2023-02-20
### Added
- usd_like_value to MinimalFund

## [1.9.40] - 2023-02-15
### Fixed
- ProfileData to profile dict portfolio

## [1.9.39] - 2023-01-18
### Fixed
- File download: typo

## [1.9.38] - 2023-01-18
### Updated
- File download: add error text when possible

## [1.9.37] - 2023-01-10
### Updated
- File download: return last_modified

## [1.9.36] - 2023-01-09
### Updated
- dependencies

## [1.9.35] - 2023-12-18
### Added
- logging callback

## [1.9.34] - 2023-12-11
### Added
- Profiles: extra_backtesting_time_frames

## [1.9.33] - 2023-12-08
### Added
- Enums: TRIGGER_HEALTH_CHECK

## [1.9.32] - 2023-12-04
### Added
- Profiles: ProfileData import

## [1.9.31] - 2023-11-16
### Added
- [Authenticator] use_as_singleton param

## [1.9.30] - 2023-10-29
### Fixed
- [Config] handle malformed pairs

## [1.9.29] - 2023-10-27
### Added
[Tree] clear
[TimeFrames] get_last_timeframe_time

## [1.9.28] - 2023-10-11
### Added
[TradingData] MinimalFund add from_value_dict

## [1.9.27] - 2023-10-11
### Updated
[TradingData] MinimalFund format

## [1.9.26] - 2023-10-11
### Added
[enums] INITIAL_PORTFOLIO_OPTIMIZATION

## [1.9.25] - 2023-10-04
### Added
[ProfileData] minimal_funds

## [1.9.24] - 2023-10-04
### Added
[Signals] add sort_signals to builder

## [1.9.23] - 2023-09-25
### Added
- [Authentication] update_orders

## [1.9.22] - 2023-09-24
### Added
- [Constants] USD_LIKE_COINS

## [1.9.21] - 2023-09-15
### Fixed
- [Config] save files issues

## [1.9.20] - 2023-09-05
### Fixed
- [Config] exchange keys format error

## [1.9.19] - 2023-09-05
### Updated
- [FlexibleDataclass] add get_field_names

## [1.9.18] - 2023-09-01
### Updated
- [FlexibleDataclass] handle any type of field

## [1.9.17] - 2023-08-25
### Added
- [Dataclasses] FlexibleDataclass

## [1.9.16] - 2023-08-22
### Added
- [Logging] extra data to exceptions

## [1.9.15] - 2023-08-17
### Added
- [Databases] is_hard_reset_error

## [1.9.14] - 2023-08-16
### Added
- [Logs] set_enable_web_interface_logs

## [1.9.13] - 2023-08-14
### Added
- [ProfileData] BacktestingContext

## [1.9.12] - 2023-08-07
### Updated
- [Authenticator] update_portfolio params

## [1.9.11] - 2023-08-07
### Updated
- ProfileData simplify content

## [1.9.10] - 2023-08-07
### Updated
- ProfileData format

## [1.9.9] - 2023-08-03
### Added
- UpdatableDataclass

## [1.9.8] - 2023-07-25
### Added
- ProfileData default values

## [1.9.7] - 2023-07-23
### Added
- ProfileData config_name

## [1.9.6] - 2023-07-22
### Added
- ProfileData
- Singletons: add remove methods

## [1.9.5] - 2023-05-17
### Added
- DEPENDENCIES to UserInputOtherSchemaValuesTypes
### Fixed
- sqlite close error
- threadpool stop

## [1.9.4] - 2023-05-10
### Updated
- [SignalBundleBuilder] add logger

## [1.9.3] - 2023-05-05
### Fixed
- make archive path

## [1.9.2] - 2023-05-02
### Updated
- setup.py

## [1.9.1] - 2023-05-02
### Updated
- setup.py

## [1.9.0] - 2023-05-02
### Updated
- Supported python versions

## [1.8.28] - 2023-04-29
### Updated
- [PrettyPrinter] decimal adapter
- [Enums] BacktestingMetadata

## [1.8.27] - 2023-04-17
### Fixed
- [Databases] SQL: delete statement

## [1.8.26] - 2023-04-15
### Updated
- [PrettyPrinter] Adapt decimals to number
### Fixed
- [Databases] Auto-repair error

## [1.8.25] - 2023-04-15
### Added
- [DisplayTranslator] config_by_tentacles
- [Databases] Auto-repair when necessary

## [1.8.24] - 2023-04-05
### Added
- [TimeFrames] is_time_frame

## [1.8.23] - 2023-03-30
### Added
- [Orders] historical orders update

## [1.8.22] - 2023-03-28
### Updated
- [AbstractTentacle] fix CLASS_UI

## [1.8.21] - 2023-03-27
### Updated
- [AbstractTentacle] add cython class and support for generalized user inputs

## [1.8.20] - 2023-03-25
### Updated
- [Profiles] add risk and complexity

## [1.8.19] - 2023-03-23
### Updated
- [Portfolio] improve portfolio pretty print

## [1.8.18] - 2023-03-22
### Added
- [User Inputs] UserInputEditorOptionsTypes
### Updated
- [Portfolio] add reference market value in pretty print

## [1.8.17] - 2023-03-21
### Updated
- [Logging] add handler-scope level update

## [1.8.16] - 2023-03-19
### Updated
- [Profiles] handle profiles sync error

## [1.8.15] - 2023-03-18
### Updated
- [PrettyPrinter] telegram lib import

## [1.8.14] - 2023-03-13
### Updated
- [Enums] Storage related enums

## [1.8.13] - 2023-03-08
### Added
- [Profiles] Validate imported profiles

## [1.8.12] - 2023-03-01
### Added
- [Databases] Debug logs

## [1.8.11] - 2023-02-16
### Updated
- [Config] Improve config files errors management

## [1.8.10] - 2023-02-12
### Updated
- [SystemResourcesWatcher] Enable resources dump in csv file

## [1.8.9] - 2023-02-11
### Updated
- [Databases] Raise FileNotFoundError on missing path

## [1.8.8] - 2023-02-10
### Added
- [Enums] TriggerSource

## [1.8.7] - 2023-02-09
### Updated
- [Databases] Add account type
- [Databases] Create file only when necessary
- [ClockSynchronizer] Disable unnecessary warning

## [1.8.6] - 2023-01-28
### Added
- [Authenticator] AccountUpdateError

## [1.8.5] - 2023-01-18
### Added
- [Authenticator] register

## [1.8.4] - 2023-01-18
### Added
- [Authenticator] update_trades and update_portfolio

## [1.8.3] - 2023-01-15
### Fixed
- [DataUtil] typing issue

## [1.8.2] - 2022-12-27
### Fixed
- [Profiles] handle invalid downloaded profiles

## [1.8.1] - 2022-12-26
### Added
- [Profiles] load_profile

## [1.8.0] - 2022-12-23
### Updated
Numpy and Cython versions

## [1.7.37] - 2022-12-22
### Added
- [Symbols] use cache for repetitive operations
- [Profiles] quite mode in install
- [DisplayTranslator] add_parts_from_other
- [ChronologicalReadDatabaseCache] reset_cached_indexes
### Updated
- [Constants] increase MAX_BACKTESTING_RUNS

## [1.7.36] 2022-12-10
### Fixed
- Profile rename

## [1.7.35] 2022-11-29
### Added
- Profiles origin url

## [1.7.34] 2022-11-24
### Fixed
- OSUtil get_cpu_and_ram_usage on different platforms

## [1.7.33] 2022-11-23
### Added
- SystemResourcesWatcher
### Updated
- [AsyncJob] add log on success after multiple failures

## [1.7.32] 2022-11-23
### Updated
- [Profiles] allow exchange removal on multiple profiles at once
### Fixed
- [ClockSynchronizer] NotImplementedError in update loop

## [1.7.31] 2022-11-11
### Fixed
- [ClockSynchronizer] on docker

## [1.7.30] 2022-11-06
### Updated
- [Profiles] install and update

## [1.7.29] 2022-11-01
### Added
- [SignalPublisher] octobot_commons.errors.MissingSignalBuilder

## [1.7.28] 2022-11-01
### Added
- [ClockSynchronizer] info log

## [1.7.27] 2022-10-27
### Fixed
- [ClockSynchronizer] Stop

## [1.7.26] 2022-10-26
### Added
- [Clock] ClockSynchronizer

## [1.7.25] 2022-10-13
### Updated
- [UserInputFactory] add update_parent_value

## [1.7.24] 2022-10-13
### Updated
- [FileSystemRunDatabasesPruner] handle no data error

## [1.7.23] 2022-10-12
### Updated
- Symbol methods

## [1.7.22] 2022-10-10
### Fixed
- Cython Database

## [1.7.21] - 2022-10-09
### Added
- User inputs
- Database pruner

## [1.7.20] - 2022-09-20
### Added
- EventTree
### Updated
- [EventTree] rename into BaseTree

## [1.7.19] - 2022-09-11
### Updated
- [Profiles] add imported attribute

## [1.7.18] - 2022-09-11
### Updated
- [Profiles] parse imported profiles

## [1.7.17] - 2022-09-08
### Added
- [Databases] live id
- [AsyncTools] timeout param

## [1.7.16] - 2022-09-02
### Added
- [Signals] Prevent double emit

## [1.7.15] - 2022-08-20
### Added
- [Signals] Signals definition and publisher

## [1.7.14] - 2022-08-19
### Updated
- [Profiles] Do not share disabled exchanges

## [1.7.13] - 2022-08-11
### Updated
- [Authenticator] API
- [AsyncTool] API

## [1.7.12] - 2022-08-10
### Updated
- [Authenticator] API

## [1.7.11] - 2022-07-16
### Added
- [Databases] add GlobalSharedMemoryStorage

## [1.7.10] - 2022-06-01
### Added
- [Symbols] Symbol object

## [1.7.9] - 2022-05-25
### Added
- [Config] exchange types
- 
## [1.7.8] - 2022-05-18
### Fixed
- [Databases] ChronologicalReadDatabaseCache set 
### Updated
- [PrettyPrinter] Orders and trades print 

## [1.7.7] - 2022-05-04
### Fixed
- [PrettyPrinter] Portfolio print 

## [1.7.6] - 2022-05-03
### Updated
- [Enums] Remove clear cache command

## [1.7.5] - 2022-05-02
### Added
- [Enums] Add databases enums
### Updated
- [Enums] rename ActivationTopics#EVALUATORS into ActivationTopics#EVALUATION_CYCLE

## [1.7.4] - 2022-04-23
### Updated
- [Databases] Add filter to get_single_sub_identifier call

## [1.7.3] - 2022-04-16
### Added
- [TradingSignals] feed bases
### Updated
- [Authenticator] Use singleton

## [1.7.2] - 2022-03-31
### Fixed
- [Databases] Cython imports

## [1.7.1] - 2022-03-30
### Added
- [Databases] CacheClient

## [1.7.0] - 2022-03-26
### Added
- [Databases] Document and relational databases
- DisplayTranslator, logical operators, multiprocessing_utils, optimization_campaigns

## [1.6.20] - 2021-01-08
### Updated
- Bump requirements

## [1.6.19] - 2021-12-19
### Added
- [PrettyPrinter] Assets support

## [1.6.18] - 2021-11-01
### Update
- [Configuration] Add merge_sub_array option in merge_dictionaries_by_appending_keys

## [1.6.17] - 2021-10-30
### Updated
- Bump requirements

## [1.6.16] - 2021-10-30
### Added 
- [Configuration] add dev_mode_enabled

## [1.6.15] - 2021-10-11
### Updated
- Bump requirements

## [1.6.14] - 2021-09-25
### Added
- OS util: parse_boolean_environment_var method

## [1.6.13] - 2021-09-14
### Added
- Singleton: get_instance_if_exists method

## [1.6.12] - 2021-09-08
### Added
- ErrorContainer: print traceback

## [1.6.11] - 2021-08-28
### Added
- Exchange CONFIG_EXCHANGE_SUB_ACCOUNT constant

## [1.6.10] - 2021-08-24
### Fixed
- Error callback registration

## [1.6.9] - 2021-08-21
### Added
- Error callback 

## [1.6.8] - 2021-08-01
### Added
- Async RLock

## [1.6.7] - 2021-07-21
### Updated
- authenticator

## [1.6.6] - 2021-07-19
### Updated
- bump requirements

## [1.6.5] - 2021-07-19
### Updated
- bump requirements

## [1.6.4] - 2021-04-06
### Updated
- loggers signatures

## [1.6.3] - 2021-05-24
### Added
- authentication abstract class

## [1.6.2] - 2021-05-05
### Updated
- bump requirements

## [1.6.1] - 2021-04-29
### Added
- [Profile import] Add replace current profile if exists parameter

## [1.6.0] - 2021-04-28
### Updated
- [Profile loading] Don't use 'default' as default profile
- [Profile loading] Load profiles only if possible and necessary

## [1.5.19] - 2021-04-06 
### Removed
- Sentry usage until performance impact is measured
 
## [1.5.18] - 2021-04-05 
### Fixed
- Sentry disable
 
## [1.5.17] - 2021-04-02 
### Added
- Sentry error tracking
 
## [1.5.16] - 2021-04-01 
### Added
- aiohttp util : download_stream_file
 
## [1.5.15] - 2021-04-01 
### Added
- is_machine_64bit and is_arm_machine to os_util
 
## [1.5.14] - 2021-03-31 
### Added
- Github constants
  
## [1.5.13] - 2021-03-28
### Fixed
- METRICS_URL constant (issue created on 1.5.12)

## [1.5.12] - 2021-03-27
### Fixed
- METRICS_URL constant

## [1.5.11] - 2021-03-23
### Added
- Symbols wildcard constant

## [1.5.10] - 2021-03-22
### Updated
- metrics url

## [1.5.9] - 2021-03-15
### Added
- Tentacles user commands

## [1.5.8] - 2021-03-04
### Added
- PriceStrings in enums

## [1.5.7] - 2021-03-03 
### Added 
- Python 3.9 support

## [1.5.6] - 2020-02-27
### Removed
- Aarch64 build on DroneCI, now build with github actions

## [1.5.5] - 2020-02-25
### Updated
- cython requirement

## [1.5.4] - 2020-02-08
### Updated
- numpy requirement

## [1.5.3] - 2020-02-03
### Updated
- numpy requirement

## [1.5.2] - 2020-01-30
### Updated
- Profiles duplication path

## [1.5.1] - 2020-12-23
### Updated
- Profiles import

## [1.5.0] - 2020-12-23
### Added
- Profiles management

## [1.4.15] - 2020-12-10
### Fixed
- trading configuration keys import

## [1.4.14] - 2020-12-08
### Updated
- migrate trading config keys into octobot-commons

## [1.4.13] - 2020-12-06
### Updated
- requirements: removed telegram requirement

## [1.4.12] - 2020-12-06
### Updated
- config.json test file

## [1.4.11] - 2020-11-26
### Added
- Thread util module

## [1.4.10] - 2020-11-25
### Updated
- Remove multi-session-profitability from default config

## [1.4.9] - 2020-11-20
### Fixed
- Number pretty printer

## [1.4.8] - 2020-11-08
### Updated
- Metrics url

## [1.4.7] - 2020-11-06
### Updated
- CI to github actions

## [1.4.6] - 2020-10-29
### Updated
- Numpy requirements

## [1.4.5] - 2020-10-24
### Updated
- Requirements

## [1.4.4] - 2020-10-23
### Added
- disable method on BotLogger

## [1.4.3] - 2020-10-23
### Updated
- Release process

## [1.4.2] - 2020-10-23
### Updated
- Python 3.8

## [1.4.1] - 2020-10-04
### Updated
- Requirements

## [1.4.0] - 2020-10-04
### Changed
- Imports

## [1.3.46] - 2020-09-02
### Updated
- AsyncJob exception handling

## [1.3.45] - 2020-08-27
### Fixed
- AsyncJob timers

## [1.3.44] - 2020-08-27
### Added
- AsyncJob

## [1.3.43] - 2020-08-15
### Updated
- Requirements

## [1.3.42] - 2020-08-13
### Removed
- Fix pretty printer typing issue 

## [1.3.41] - 2020-07-25
### Removed
- search_class_name_in_class_list from tentacles manager 

## [1.3.40] - 2020-06-28
### Updated
- Requirements

## [1.3.39] - 2020-06-27
### Fixed
- Errors counter

## [1.3.38] - 2020-06-19
### Updated
- Requirements

## [1.3.37] - 2020-06-09
### Updated
- Asyncio tools ErrorContainer

## [1.3.36] - 2020-06-02
### Added
- Asyncio tool wait_for_task_to_perform

## [1.3.35] - 2020-06-02
### Added
- get_password_hash

## [1.3.34] - 2020-05-27
### Update
- Cython version

## [1.3.33] - 2020-05-20
### Update
- Take config schema as argument in config management

## [1.3.32] - 2020-05-19
### Fixed
- Cython header

## [1.3.31] - 2020-05-16
### Updated
- Requirements

## [1.3.30] - 2020-05-14
### Added
- [Enums] ChannelConsumerPriorityLevels

## [1.3.29] - 2020-05-13
### Fixed
- [PrettyPrinter] Fix trade_pretty_printer cython header

## [1.3.28] - 2020-05-12
### Fixed
- [Logging] Fix get_backtesting_errors_count cython header

## [1.3.27] - 2020-05-11
### Added
- [ConfigUtil] Decrypt util function

## [1.3.26] - 2020-05-11
### Added
- [CI] Azure pipeline

### Removed
- [CI] macOs build on travis
- [CI] Appveyor builds

## [1.3.25] - 2020-05-10
### Updated
- Telegram requirements

## [1.3.24] - 2020-05-09
### Added
- OctoBotChannel subjects enum

## [1.3.23] - 2020-05-09
### Fixed
- Evaluators channels name

## [1.3.22] - 2020-05-09
### Added
- OctoBot channel name

## [1.3.21] - 2020-05-08
### Update
- improve asyncio ErrorContainer

## [1.3.20] - 2020-05-08
### Fixed
- asyncio ErrorContainer

## [1.3.19] - 2020-05-07
### Added
- asyncio ErrorContainer

## [1.3.18] - 2020-05-06
### Fixed
- Logging_util compiled errors

## [1.3.17] - 2020-05-05
### Fixed
- Logging_util cython headers

## [1.3.16] - 2020-05-03
### Added
- time_frame_manager cythonization and tests
- symbol_util cythonization

## [1.3.15] - 2020-05-03
### Removed
- [EventTree] Events management

## [1.3.14] - 2020-05-02
### Added
- list_util file with flatten_list method

## [1.3.13] - 2020-04-30
### Added
- Pylint and Black code style checkers

### Fixed
- Code style issues

### Removed
- Singleton annotation
- get_value_or_default replaced by native dict.get

## [1.3.12] - 2020-04-27
### Updated
- Cython requirement

## [1.3.11] - 2020-04-23
### Updated
- [DataUtil] Improve shift implementation

## [1.3.10] - 2020-04-16
### Added
- Evaluators channel name
- [EventTree] node value time

### Fixed
- [EventTree] event clearing too early
- [EventTree] syntax

### Removed
- AbtractEvaluator default description

## [1.3.9] - 2020-04-10
### Fixed
- Missing constant

## [1.3.8] - 2020-04-08
### Removed
- AbstractTentacle cythonization

## [1.3.7] - 2020-04-07
### Fixed
- Wildcard imports

## [1.3.6] - 2020-03-25
### Updated
- Tentacles management to include OctoBot-tentacles-manager

## [1.3.5] - 2020-03-25
### Updated
- [Requirement] cython to 0.29.16
- [Requirement] numpy to 0.18.2
- [Requirement] jsonschema to 3.2.0
- [Requirement] python-telegram-bot to 12.4.2

## [1.3.4] - 2020-03-22
### Added
- Liquidations, Mini ticker and Book ticker Channels name

## [1.3.3] - 2020-03-15
### Added
- Datetime to timestamp conversion

## [1.3.2] - 2020-03-14
### Added
- Funding Channel name

## [1.3.1] - 2020-03-07
### Added
- Margin Portfolio key

## [1.3.0] - 2020-03-05
### Added
- Error message to exception logger

### Fixed
- Trade prettyprinter format

## [1.2.3] - 2020-02-16
### Added
- shift_value_array function to shift a numpy array
- Cythonized numpy array functions
- Error notifier callback 

### Changed
- Minimal time frame is now 1 min 
- Update pretty_printer for the new Trade attributes

## [1.2.2] - 2020-01-04
### Changed
- Pretty printer cryptocurrencies alert refresh

### Fixed
- MarkdownFormat comparison error

## [1.2.1] - 2020-01-02
### Added
- Asyncio run_coroutine_in_asyncio_loop method
- External resources management
- Tentacle and classes management utility methods
- Configuration file management

### Changed
- Pretty printer typo fix 

## [1.2.0] - 2019-12-18
### Added
- Tests from OctoBot < 0.4.0
- Number Util float rounding method
- Evaluators_util cython compilation

### Changed
- TimeFrameManager static methods to function only
- DataUtil static methods to function only
- Evaluator_util check_eval_note returns only boolean

### Removed
- Travis build stage

## [1.1.53] - 2019-12-17
### Added
- Makefile

### Fixed
- SegFault : Temporary disable abstract_tentacle cython compilation

## [1.1.52] - 2019-12-14
###  Added
- EventTree NodeExistsError exception

## [1.1.51] - 2019-12-14
### Added
- EventTree methods relative node param
- EventTree get without creation method

## [1.1.50] - 2019-12-11
### Added
- EventTree with EventNode classes
- tests EventTree methods

## [1.1.49] - 2019-11-07
## Updated
- Cython version to 0.29.14

## [1.1.48] - 2019-10-21
### Added
- OSX support

## [1.1.47] - 2019-10-19
### Added
- OS tools

## [1.1.46] - 2019-10-09
### Changed
- Code cleanup

## [1.1.45] - 2019-10-09
### Added
- Appveyor CI

## [1.1.44] - 2019-10-09
### Added
- PyPi manylinux deployment

## [1.1.43] - 2019-10-08
### Fixed
- Install with setup

## [1.1.42] - 2019-10-03
### Added
- Advanced Manager new search methods

## [1.1.41] - 2019-10-02
### Added
- Time constants

## [1.1.40] - 2019-09-26
### Added
- Inspector deep method by subclasses

## [1.1.39] - 2019-09-26
### Added
- Inspector method by subclasses

## [1.1.38] - 2019-09-25
### Fixed
- Setup installation

## [1.1.37] - 2019-09-21
### Added
- class_inspector default_parents_inspection method

## [1.1.36] - 2019-09-18
### Added
- class_inspector cython compilation

### Changed
- 'default_parent_inspection' to public

## [1.1.35] - 2019-09-17
### Changed
- TIME_CHANNEL to backtesting names

## [1.1.34] - 2019-09-12
### Fixed
- is_valid_timestamp method exception

## [1.1.33] - 2019-09-01
### Fixed
- Adapted config manager from OctoBot core

## [1.1.32] - 2019-08-27
### Added
- Tentacle config manager

## [1.1.31] - 2019-08-18
### Removed
- Abstract tentacle pxd file

## [1.1.30] - 2019-08-17
### Removed
- Advanced manager class

## [1.1.29] - 2019-08-16
### Changed
- Generify & cythonize advanced_manager

## [1.1.28] - 2019-08-16
### Added
- Evaluator util

## [1.1.27] - 2019-08-15
### Added
- Future tentacles constants declaration

## [1.1.26] - 2019-08-15
### Added
- Abstract tentacle cython declaration

## [1.1.25] - 2019-08-15
### Added
- OctoBot custom errors (can be used to except elsewhere)

## [1.1.24] - 2019-08-15
### Added
- Tentacles commons constants

## [1.1.23] - 2019-08-15
### Added
- Common channels name

## [1.1.22] - 2019-08-14
### Fixed
- Singleton Class instances attribute declaration

## [1.1.21] - 2019-08-14
### Changed
- Singleton Class implementation

## [1.1.20] - 2019-08-14
### Added
- Singleton Class
- Cython compilation

### Changed
- Moved singleton.py to singleton/singleton_annotation.py

## [1.1.19] - 2019-08-14
### Changed
- AdvancedManager fully split Evaluators and Trading tentacles classes list initialization

## [1.1.18] - 2019-08-07
### Added
- ConfigManager from OctoBot main repository

### Changed
- AdvancedManager tentacle initialization is now splitted between Evaluators and Trading

## [1.1.17] - 2019-08-06
### Added
- Constants from OctoBot-Tentacles-Manager

## [1.1.16] - 2019-08-05
### Changed
- Tentacles management imports to prepare OctoBot-Tentacles-Manager migration to commons

## [1.1.15] - 2019-08-05
### Added
- Config load methods
- 6h time frame in TimeFrames enums

## [1.1.14] - 2019-08-01
### Changed
- Adapt pretty printer to OctoBot-Trading callbacks (exchange name)
- Updated order and trade instance getters/property compatibilities

## [1.1.13] - 2019-06-23
### Changed
- Catch split_symbol index error exception

## [1.1.12] - 2019-06-09
### Added
- Encrypt and decrypt functions

## [1.1.11] - 2019-06-08
### Added
- Config util

## [1.1.10] - 2019-06-08
### Added
- Data util
- Numpy requirement

## [1.1.9] - 2019-06-06
### Added
- Trading constants from OctoBot constants

## [1.1.8] - 2019-06-05
### Added
- TimeFrames enums
- TimeFrame manager

## [1.1.7] - 2019-06-05
### Added
- dict util methods

### Removed
- Initializable class

## [1.1.6] - 2019-06-05
### Added
- pretty printer

## [1.1.5] - 2019-06-02
### Changed
- convert_symbol new optionnal parameter should_lowercase with False as default value 

## [1.1.4] - 2019-06-01
### Added
- convert_symbol method to manage separator between symbol formats
### Changed
- merge_currencies with a new additional parameter "separator" with MARKET_SEPARATOR as default value

## [1.1.3] - 2019-05-27
### Added
- Manifest

## [1.1.2] - 2019-05-27
### Added
- Symbol utils
- Initializable class
