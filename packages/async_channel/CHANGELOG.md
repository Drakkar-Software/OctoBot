# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.2] - 2026-01-03
### Added
- Detailed typing to all classes

## [2.2.1] - 2023-09-03
### Added
- channel_name to creator

## [2.2.0] - 2023-05-02
### Updated
- Supported python versions
### Removed
- Cython

## [2.1.0] - 2022-12-23
### Updated
- [Cython] update to 0.29.32

## [2.0.14] - 2022-12-22
### Added
- [Channel] get_prioritized_consumers

## [2.0.13] - 2022-01-08
### Added
- [SupervisedConsumer] add ability to join current perform task

### Updated
- bump requirements

## [2.0.12] - 2021-07-19
### Updated
- bump requirements

## [2.0.11] - 2021-07-19
### Updated
- bump requirements

## [2.0.10] - 2021-05-05
### Updated
- bump requirements

## [2.0.9] - 2021-03-03 
### Added 
- Python 3.9 support

## [2.0.8] - 2021-02-25
### Updated
- cython requirement

## [2.0.7] - 2020-12-07
### Updated
- revert import statements changes

## [2.0.6] - 2020-11-07
### Updated
- revert import statements changes

## [2.0.5] - 2020-11-07
### Updated
- import statements

## [2.0.4] - 2020-11-07
### Fixed
- async_channel.util python file

## [2.0.3] - 2020-10-23
### Updated
- Python 3.8 support

## [2.0.2] - 2020-10-13
### Fixed
- Cython headers export

## [2.0.1] - 2020-10-01
### Added
- Logging dynamic implementation
- Project name to 'Async-Channel'

## [2.0.0] - 2020-10-01
### Update
- Project name to 'channel'
- python and cython imports behaviour

### Removed
- OctoBot-Commons requirement

## [1.4.11] - 2020-09-01
### Update
- Requirements

## [1.4.10] - 2020-08-15
### Update
- Requirements

## [1.4.9] - 2020-06-19
### Update
- Requirements

## [1.4.8] - 2020-05-27
### Update
- Cython version

## [1.4.7] - 2020-05-17
### Fixed
- [Producer] pause is running was not set

## [1.4.6] - 2020-05-16
### Updated
- Requirements

## [1.4.5] - 2020-05-13
### Changed
- [Channel] Default priority value to HIGH

## [1.4.4] - 2020-05-13
### Added
- [Channel] Producer pause and resume check with consumer priority levels

## [1.4.2] - 2020-05-11
### Added
- [CI] Azure pipeline

### Removed
- [CI] macOs build on travis
- [CI] Appveyor builds

## [1.4.1] - 2020-05-09
### Added
- [ChannelInstances] Channel id support

## [1.4.0] - 2020-05-01
### Added
- Synchronous Channel
- Synchronous Consumer
- Synchronous Producer

## [1.3.25] - 2020-04-27
### Added
- [Channel] consumer filtering by list

## [1.3.24] - 2020-04-17
### Added
- [Producer] pause and resume default implementation

## [1.3.23] - 2020-04-07
### Fixed
- Wildcard imports

## [1.3.22] - 2020-03-26
### Added
- Documentation basis with sphinx
- Pylint check on CI
- Black check on CI

### Fixed
- Documentation issues
- Pylint issues
- Black issues

## [1.3.21] - 2020-03-05
### Changed
- Exception logger from Commons

### Updated
- Commons version to >= 1.3.0

## [1.3.20] - 2020-02-10
### Added
- flush method to channels
- ```__str__``` representation for consumers

## [1.3.19] - 2020-01-02
### Changed
- create_channel_instance now returns the created channel

### Fixed
- fix set_chan channel name default value inference

## [1.3.18] - 2019-12-24
### Changed
- Channels __ methods to _ methods (syntax update)

## [1.3.17] - 2019-12-21
### Updated
- Commons version to >= 1.2.0

### Added
- Makefile

## [1.3.16] - 2019-12-14
### Updated
- Commons version to >= 1.1.50

### Fixed
- test_set_chan

## [1.3.15] - 2019-11-07
### Updated
- Cython version to 0.29.14

## [1.3.14] - 2019-10-29
### Added
- OSX support

## [1.3.13] - 2019-10-09
### Added
- PyPi manylinux deployment

## [1.3.12] - 2019-10-08
### Fixed
- Install with setup

## [1.3.11] - 2019-10-07
### Added
- CancelledError catching in consume task

## [1.3.10] - 2019-10-05
### Added
- Producer is_running attribute

## [1.3.9] - 2019-10-03
### Added
- Check if the new producer is already registered before channel registration

## [1.3.8] - 2019-10-02
### Fixed
- kwargs argument cython compatibility

## [1.3.7] - 2019-09-25
### Changed
- Cython compilation directives (optimization purposes)

## [1.3.6] - 2019-09-22
### Fixed
- Fix internal consumer callback

## [1.3.5] - 2019-09-21
### Fixed
- Travis channel '__check_producers_state()' method crash when compiled

## [1.3.4] - 2019-09-09
### Fixed
- Producer 'wait_for_processing' declaration

## [1.3.3] - 2019-09-08
### Changed
- Channel 'get_consumer_from_filters' manage wildcard filters

## Related issue
- #9 [Channel] Implement consumer filter

## [1.3.2] - 2019-09-07
### Changed
- Channel 'get_consumer_from_filters' method compilation from cython to python

## [1.3.1] - 2019-09-07
### Added
- Producer supervised consumer wait method 'wait_for_processing'

### Changed
- Consumer tests

## [1.3.0] - 2019-09-07
### Added
- Supervised Consumer that notify the consumption end

### Fixed
- Consumer tests

## [1.2.0] - 2019-09-04
### Added
- Channel add_new_consumer method to add a new consumer with filters
- Channel get_consumer_from_filters to get a list of consumers that match with filters

### Changed
- Channel new_consumer method can handle a consumer filters dict
- Channel __add_new_consumer_and_run to use consumer filters and not consumer name

## [1.1.14] - 2019-08-29
### Added
- Tests

## [1.1.13] - 2019-08-29
### Fixed
- Internal consumer implementation

## [1.1.12] - 2019-08-29
### Fixed
- Internal consumer consume method

## [1.1.11] - 2019-08-28
### Added
- Internal consumer : the callback is defined into the consumer class and is not a constructor param anymore

## [1.1.10] - 2019-08-27
### Added
- Consumer instance param in channel new_consumer to handle a new consumer with an already created instance

## [1.1.9] - 2019-08-26
### Fixed
- Queue to async

## [1.1.8] - 2019-08-16
### Changed
- Replaced Channels class by orphan public methods

### Removed
- Channels class

## [1.1.7] - 2019-08-14
### Added
- Setup install requirements

## [1.1.6] - 2019-08-14
### Changed
- ChannelInstances class to commons singleton class implementation

## [1.1.5] - 2019-08-13
### Fixed
- Changed Producer attributes to public
- Changed Consumer attributes to public

## [1.1.4] - 2019-08-13
### Fixed
- Channel is_paused attribute to public

## [1.1.3] - 2019-08-13
### Added
- Producer pause and resume methods
- Channel producers pause/resume management

### Related issue
- [Producer] Implement channel pause and resume #8 

## [1.1.2] - 2019-08-12
### Fixed
- Channel init_consumer_if_necessary object key type

## [1.1.1] - 2019-08-12
### Fixed
- Channel init_consumer_if_necessary iterable type

## [1.1.0] - 2019-08-11
### Added
- Channel global tests

### Changed
- Migrate Consumer start, run and stop methods to async

### Fixed
- Consumer attributes queue and filter_size to public
- Channel start and stop methods
- Channels methods Cython compliance

## [1.0.12] - 2019-08-09
### Changed
- PyDoc fixes

## [1.0.11] - 2019-08-09
### Added
- Channel new consumer methods

## [1.0.10] - 2019-08-08
### Added
- Channel internal_producer

## [1.0.9] - 2019-08-07
### Changed
- Channel creation utility refactored in two different methods

## [1.0.8] - 2019-08-06
### Added
- Channel creation utility

## [1.0.7] - 2019-08-04
### Added
- Channel 'modify' method that calls all producers modify method
- Channel 'register_producer' method to register all its producers.

## [1.0.6] - 2019-08-03
### Added
- constants.py file

### Modified 
- Import way with __init__.py files

### Removed
- Unused evaluator package

## [1.0.5] - 2019-08-03
### Added
- Producer 'modify' method

## [1.0.4] - 2019-06-10
### Fixed
- ExchangeChannel deprecated imports

## [1.0.3] - 2019-06-10
### Removed
- [OctoBot-Trading] migrate exchange channels to OctoBot-Trading

## [1.0.2] - 2019-06-09
### Fixed
- [OctoBot-Trading] Exchange get_name() method deprecated

## [1.0.1] - 2019-05-27
### Changed
- Migrate to cython with pure python
