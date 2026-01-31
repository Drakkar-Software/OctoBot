# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.11.0] - 2026-01-25
### Added
[Tentacles] add Agents tentacle type

## [2.10.0] - 2026-01-06
### Updated 
[Requirements] Bump OctoBot-Commons version

## [2.9.19] - 2025-11-26
### Added 
[Requirements] [full] requirements installation

## [2.9.18] - 2025-11-18
### Updated
[Tentacles] add DSL operator type

## [2.9.17] - 2025-09-12
### Updated
[Dependencies] bump packaging to 25.0

## [2.9.16] - 2023-08-19
### Updated
[API] use ref config registered tentacles

## [2.9.15] - 2023-07-04
### Added
[Logging] add option to hide url

## [2.9.14] - 2023-07-04
### Added
[API] import_registered_tentacles to fill_with_installed_tentacles

## [2.9.13] - 2023-07-03
### Added
[API] return value on save_config

## [2.9.12] - 2023-07-03
### Added
[API] packages methods

## [2.9.11] - 2023-02-18
### Fixed
- SSL certificate issues

## [2.9.10] - 2023-02-13
### Added
- API: register_extra_tentacle_data

## [2.9.9] - 2023-01-18
### Updated
- tentacles: log url on fetching error

## [2.9.8] - 2023-01-10
### Updated
- tentacles: log artifact modification date and hash

## [2.9.7] - 2023-01-09
### Updated
- dependencies

## [2.9.6] - 2023-12-04
### Added
- API: fill_with_installed_tentacles

## [2.9.5] - 2023-09-15
### Updated
- Config: improve config save

## [2.9.4] - 2023-08-22
### Added
- API: ensure_tentacle_info

## [2.9.3] - 2023-08-05
### Added
- API: set_tentacle_config_proxy context manager

## [2.9.2] - 2023-07-23
### Added
- API: set_tentacle_config_proxy
### Updated
- TentaclesSetupConfiguration#from_activated_tentacles_classes: accept tentacles classes as str

## [2.9.1] - 2023-05-05
### Fixed
- Disable tentacles error

## [2.9.0] - 2023-05-02
### Updated
- Supported python versions

## [2.8.6] - 2022-04-15
### Added
- [API] add deactivate_all 

## [2.8.5] - 2022-03-27
### Added
- [API] add get_tentacles_classes_names_for_type 

## [2.8.4] - 2022-02-16
### Updated
- [Configuration] Improve configuration file error management 

## [2.8.3] - 2022-01-29
### Fixed
- [Automation] Now extract automation tentacles

## [2.8.2] - 2022-01-28
### Added
- [Tentacle type] Automation

## [2.8.1] - 2022-12-26
### Updated
- [TentaclesSetupConfiguration] use default config in fixer

## [2.8.0] - 2022-12-23
### Updated
- OctoBot-Commons requirement

## [2.7.5] - 2022-12-22
### Added
- [Installer] quite mode in profile install

## [2.7.4] - 2022-11-02
### Fixed
- Metadat file creation while exporting tentacles

## [2.7.3] - 2022-10-13
### Updated
- use packaging.version 

## [2.7.2] - 2022-09-12
### Added
- refresh_profile_tentacles_setup_config 

## [2.7.1] - 2022-09-11
### Updated
- Skip installation_context update on imported profiles 

## [2.7.0] - 2022-03-30
### Added
- Scripted lib requirements

## [2.6.5] - 2022-02-18
### Updated
- Bump requirements to fix jinja deprecation issue

## [2.6.4] - 2022-01-08
### Updated
- Bump requirements

## [2.6.3] - 2021-11-18
### Updated
- Aiohttp requirement

## [2.6.2] - 2021-09-28
### Added
- [Supervisor] Path and default deactivation 

## [2.6.1] - 2021-09-25
### Fixed
- Cli attribute

## [2.6.0] - 2021-09-16
### Added
- S3 uploader

## [2.5.3] - 2021-09-13
### Updated
- Tentacles repository url

## [2.5.2] - 2021-06-03
### Fixed
- Tentacles activation default values using reference tentacles

## [2.5.1] - 2021-05-08
### Fixed
- get_tentacle_module_path return value when tentacle is not found

## [2.5.0] - 2021-05-05
### Added
- profile replacement when exists

### Updated
- [TentacleSetupConfiguration] Fix tentacle not in config activation filter

### Removed 
- tentacle reference config duplications

## [2.4.13] - 2021-04-28
### Updated
- CURRENT_DIR_PATH to os.getcwd()

## [2.4.12] - 2021-04-27
### Added
- profiles folder to arch

## [2.4.11] - 2021-04-02
### Added
- Installation context in tentacle_config.json

## [2.4.10] - 2021-04-01 
### Added
- aiohttp_util download_stream_file usage
 
## [2.4.9] - 2021-03-22 
### Updated 
- tentacles url

## [2.4.8] - 2021-03-06 
### Updated 
- Force chardet version

## [2.4.7] - 2021-03-03 
### Added 
- Python 3.9 support

## [2.4.6] - 2021-02-25
### Updated
- Requirements

## [2.4.5] - 2021-01-19
### Added
- Metadata fields description, short_name and tags

## [2.4.4] - 2021-01-18
### Added
- Metadata export for full tentacle packages
- Metadata injection after generation

## [2.4.3] - 2021-01-07
### Updated
- Exported package name with the os and architecture name if compiled else any_platform

## [2.4.2] - 2020-12-29
### Fixed
- Missing reference_tentacles directory at zip root

## [2.4.1] - 2020-12-29
### Fixed
- Previous folder export from package name

## [2.4.0] - 2020-12-28
### Updated
- Models refactor

### Added
- Exporter for each model
- Nexus uploader

## [2.3.9] - 2020-12-23
### Added
- Profiles handling

## [2.3.8] - 2020-12-06
### Fixed
- CLI arguments

## [2.3.7] - 2020-12-06
### Added
- Tentacles package filter

## [2.3.6] - 2020-11-25
### Updated
- Improved import tentacles error message

## [2.3.5] - 2020-10-29
### Updated
- Commons requirement

## [2.3.4] - 2020-10-25
### Updated
- Aiofiles requirement

## [2.3.3] - 2020-10-24
### Updated
- Aiohttp requirement

## [2.3.2] - 2020-10-23
### Updated
- Python 3.8 support

## [2.3.1] - 2020-10-09
### Fixed
- Cli imports

## [2.3.0] - 2020-10-05
### Changed
- Imports

## [2.2.5] - 2020-09-05
### Added
- with_class_method in Configurator

## [2.2.4] - 2020-08-18
### Added
- Python entrypoint

## [2.2.3] - 2020-08-15
### Update
- Requirements

## [2.2.2] - 2020-07-26
### Added
- get_class_from_name_with_activated_required_tentacles in configurator API

## [2.2.1] - 2020-07-25
### Fixed
- Issues with multiple Cython compilation in a row
- Do not include non-tentacle related elements in packed tentacles

## [2.2.0] - 2020-06-28
### Added
- Support for tentacles class names in inspector API
- Tentacle group in metadata
### Updated
- Tentacle activation sorted by tentacle type

## [2.1.7] - 2020-05-28
### Updated
- Strictly check tentacles folders in is_tentacles_arch_valid

## [2.1.6] - 2020-05-28
### Added
- Bot config dir in cli handler

## [2.1.5] - 2020-05-27
### Update
- Cython version

## [2.1.4] - 2020-05-20
### Added
- Tentacles default activation file path

## [2.1.3] - 2020-05-15
### Added
- Tentacles package origin location management

## [2.1.2] - 2020-05-10
### Update
- Configurator API

## [2.1.1] - 2020-05-8
### Update
- Configurator API

## [2.1.0] - 2020-05-6
### Updated
- Use sync file IO for bot interactions

## [2.0.5] - 2020-05-4
### Added
- Quite mode
- Error on tentacles package not found when downloading

## [2.0.4] - 2020-05-1
### Fixed
- Migrate interfaces and notification into services

## [2.0.3] - 2020-04-25
### Fixed
- Use user path or url in tentacles requirements

## [2.0.2] - 2020-04-13
### Fixed
- Crash when missing config folder

## [2.0.1] - 2020-04-10
### Added
- Dev mode

### Fixed
- Import issues
- Logger issues

### Removed
- Websocket tentacle type

Changelog for 2.0.0
====================
*Released date : March 31 2020*

Total rework of the OctoBot Tentacles Manager for OctoBot 0.4
# New feature :
    - APIs and CLI for each action
    - Async file management
    - Tentacles packages management
    - Tentacles configuration management
    - Tentacles loading management
    
Changelog for 1.0.13
====================
*Released date : December 28 2019*

# New feature :
    - Disable specify tentacle target directory

Changelog for 1.0.12
====================
*Released date : September 16 2019*

# New feature :
    - Can now specify the tentacle target directory

Changelog for 1.0.11
====================
*Released date : June 2 2019*

# New feature :
    - Now store tentacles config schemas as well as tentacles config in default folder
# Bug fix :
    - Fixed config file sometimes not created on tentacles update

Changelog for 1.0.10
====================
*Released date : Mai 8 2019*

# New feature :
    - Fixed import error

Changelog for 1.0.9
====================
*Released date : Mai 5 2019*

# New feature :
    - Handle config schema
   
Changelog for 1.0.8
====================
*Released date : April 14 2019*

# New feature :
    - Log hotfix
   
Changelog for 1.0.7
====================
*Released date : April 14 2019*

# New feature :
    - Now do not display in dev tentacles when update or uninstall if dev mode is not activated

Changelog for 1.0.6
====================
*Released date : April 13 2019*

# New feature :
    - Install now only reset tentacle config file if config file is missing

Changelog for 1.0.5
====================
*Released date : February 17 2019*

# New feature :
    - Can now specify a github branch using default_git_branch argument in parse_commands or by adding the branch argument in command argument in parse_commands
====================
*Released date : February 7 2019*

# Bug fixes :
    - Fix tentacle creator

Changelog for 1.0.3
====================
*Released date : February 7 2019*

# Bug fixes :
    - Fix init file creation & update
