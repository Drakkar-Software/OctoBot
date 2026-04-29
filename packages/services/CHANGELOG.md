# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.0] - 2026-02-02
### Added
- pydantic to requirements
- add AbstractAIService
- add AbstractWebSearchService
- MCP server interface
### Updated
- OpenAI dependency

## [1.7.3] - 2026-01-29
### Added
- Tavily service constants
- Bird service constants

## [1.7.2] - 2026-01-25
### Added
- Coingecko service constants

## [1.7.1] - 2026-01-25
### Added
- Add `get_data_cache` to `AbstractServiceFeed`

## [1.7.0] - 2026-01-23
### Updated
- Dependencies

## [1.6.31] - 2026-01-22
### Added 
- Add exchange service constants

## [1.6.30] - 2024-11-27
### Updated 
[Requirements] moved openai to the [full] requirements

## [1.6.29] - 2025-11-26
### Added 
[Requirements] [full] requirements installation

## [1.6.28] - 2025-10-28
### Added
- Add `data_cache` to `AbstractServiceFeed`

## [1.6.27] - 2025-10-28
### Added
- Coindesk, Lunarcrush and Alternative.me services constants

## [1.6.26] - 2025-08-24
### Updated
- Dependencies

## [1.6.25] - 2025-08-17
### Updated
- Dependencies

## [1.6.24] - 2025-05-14
### Updated
- Dependencies

## [1.6.23] - 2025-01-09
### Updated
- Dependencies

## [1.6.22] - 2025-01-04
### Updated
- Dependencies

## [1.6.21] - 2023-10-21
### Added
[Constant] add CONFIG_LLM_CUSTOM_BASE_URL

## [1.6.20] - 2023-10-07
### Added
[ReadOnlyInfo] add CTA type

## [1.6.19] - 2023-10-03
### Added
- ReadOnlyInfo
### Updated
- Dependencies

## [1.6.18] - 2023-09-03
### Updated
- Requirements: bump flask-cors

## [1.6.17] - 2023-08-19
### Updated
- Requirements: bump

## [1.6.16] - 2023-07-23
### Updated
- Orders notifications: Use PNL

## [1.6.15] - 2023-06-25
### Added
- AbstractService: is_improved_by_extensions

## [1.6.14] - 2023-06-12
### Added
- Constants: webhook constants

## [1.6.13] - 2023-03-31
### Updated
- Requirements: bump

## [1.6.12] - 2023-03-28
### Updated
- Interfaces: improve wildcard trading mode display

## [1.6.11] - 2023-02-28
### Updated
- Services: add help url to creation_error_message

## [1.6.10] - 2023-01-10
### Added
- Services: creation_error_message

## [1.6.9] - 2023-01-09
### Updated
- fix openai patches by patch_openai_proxies

## [1.6.8] - 2023-01-09
### Added
- is_openai_proxy

## [1.6.7] - 2023-01-09
### Updated
- dependencies

## [1.6.6] - 2023-12-18
### Added
- [interfaces] async api

## [1.6.5] - 2023-10-27
### Added
- [get_service] config param

## [1.6.4] - 2023-10-11
### Added
- [Webhook] Add CONFIG_NGROK_DOMAIN key

## [1.6.3] - 2023-10-01
### Updated
- [Requirements] update dependencies

## [1.6.2] - 2023-08-18
### Updated
- [Requirements] update dependencies

## [1.6.1] - 2023-07-23
### Updated
- [ReturningStartable] add threaded_start

## [1.6.0] - 2023-05-02
### Updated
- Supported python versions

## [1.5.6] - 2023-05-02
### Updated
- [Dependencies] flask, ngrok and openai

## [1.5.5] - 2023-04-23
### Updated
- [BotInterface] set_risk command now updated edited config

## [1.5.4] - 2023-03-30
### Updated
- [Orders] Order channel callback

## [1.5.3] - 2023-03-29
### Added
- [Services] Add GPT requirements
### Updated
- [Services] Dependencies

## [1.5.2] - 2023-03-24
### Updated
- [Services] Improve portfolio output

## [1.5.1] - 2023-03-22
### Updated
- [Services] Add reference market value in portfolio pretty print

## [1.5.0] - 2023-03-15
### Updated
- [Services] stop is now async
- [Telegram] migrate to async version of the lib

## [1.4.4] - 2023-03-01
### Updated
- [API] trading apis

## [1.4.3] - 2023-02-04
### Updated
- [NotificationLevel] replace DANGER by ERROR

## [1.4.2] - 2023-02-03
### Removed
- [Requirements] Python-Twitter as Twitter API will become paid only

## [1.4.1] - 2022-12-29
### Added
- [Requirements] flask_cors

## [1.4.0] - 2022-12-23
### Updated
- [Requirements] Bump

## [1.3.10] - 2022-12-13
### Updated
- [Requirements] Restore gevent==22.10.2

## [1.3.9] - 2022-12-11
### Updated
- [Requirements] Restore gevent==21.12.0 due to glibc incompatibility (https://github.com/gevent/gevent/blob/master/CHANGES.rst#22102-2022-10-31)

## [1.3.8] - 2022-12-09
### Updated
- [Requirements] bump requirements

## [1.3.7] - 2022-10-17
### Updated
- [Positions] close position

## [1.3.6] - 2022-09-08
### Updated
- [AsyncTools] add timeout param

## [1.3.5] - 2022-08-25
### Updated
- [Dependencies] update to latest reddit, telegram, ngrok and flask versions

## [1.3.4] - 2022-08-11
### Updated
- [AsyncTools] add log_exceptions param

## [1.3.3] - 2022-07-29
### Updated
- [Requirements] bump web interface requirements

## [1.3.2] - 2022-07-02
### Updated
- [Requirements] bump requirements

## [1.3.1] - 2022-06-06
### Updated
- [Notifications] always create notification channel

## [1.3.0] - 2022-05-04
### Added
- Notification sounds
### Updated
- Flask requirement

## [1.2.32] - 2022-02-18
### Updated
- Flask requirement

## [1.2.31] - 2022-01-20
### Updated
- requirements

## [1.2.30] - 2022-01-16
### Updated
- requirements

### Fixed
- [Telegram] RPC login error

## [1.2.29] - 2021-12-19
### Updated
- [Util][Portfolio] Migrate to assets

## [1.2.28] - 2021-11-24
### Added
- [Constants] CONFIG_ENABLE_NGROK

## [1.2.27] - 2021-10-28
### Added
- flask-compress requirements
- flask-cache requirements

## [1.2.26] - 2021-09-21
### Updated
- requirements

## [1.2.25] - 2021-09-13
### Added
- AbstractBotInterface set_command_restart method

## [1.2.24] - 2021-09-03
### Updated
- requirements

## [1.2.23] - 2021-07-28
### Updated
- requirements

## [1.2.22] - 2021-07-17
### Updated
- changed missing configuration warning into info
- requirements

## [1.2.21] - 2021-07-09
### Updated
- requirements

## [1.2.20] - 2021-07-03
### Added
- CONFIG_ENABLE_NGROK constants
- CONFIG_WEBHOOK_SERVER_IP
- CONFIG_WEBHOOK_SERVER_PORT

## [1.2.19] - 2021-05-03
### Added
- async reddit api via asyncpraw
### Updated
- gevent and python-telegram-bot versions

## [1.2.18] - 2021-04-22
### Updated
- simplifiedpytrends version

## [1.2.17] - 2021-04-14
### Added
- CONFIG_MEDIA_PATH constant

## [1.2.16] - 2021-04-09
### Added
- telethon
- telegram api constants

## [1.2.15] - 2021-04-08
### Updated
- pyngrok version

## [1.2.14] - 2021-03-26
### Updated
- Requirements
 
## [1.2.13] - 2021-03-15 
### Added 
- User commands channel

## [1.2.12] - 2021-03-03 
### Added 
- Python 3.9 support

## [1.2.11] - 2020-01-04
### Updated
- requirements

## [1.2.10] - 2020-12-23
### Fixed
- has_trader exception

## [1.2.9] - 2020-12-23
### Added
- Profiles handling
### Fixed
- No activated trader situations

## [1.2.8] - 2020-12-16
### Updated
- Push notifications using async executor
- flask-socketio to 5.0.0

## [1.2.7] - 2020-12-06
### Fixed
- Notifiers when no config data

## [1.2.6] - 2020-11-26
### Added
- Services logo and url

## [1.2.5] - 2020-11-14
### Added
- Services logo and url

## [1.2.4] - 2020-11-07
### Updated
- Requirements

## [1.2.3] - 2020-10-27
### Updated
- Services warnings and errors on config issues

## [1.2.2] - 2020-10-26
### Updated
- Requirements

### Fixed
- Service init

## [1.2.1] - 2020-10-23
### Updated
- Python 3.8 support

## [1.2.0] - 2020-10-06
### Updated
- Migrate imports

## [1.1.22] - 2020-09-02
### Updated
- Order notifications for new order states management

## [1.1.21] - 2020-08-31
### Updated
- Order notifications for new order states management

## [1.1.20] - 2020-08-23
### Updated
- Requirements

## [1.1.19] - 2020-08-15
### Updated
- Requirements

## [1.1.18] - 2020-07-19
### Updated
- Refresh real trader changed into refresh portfolio
- Requirements

## [1.1.17] - 2020-06-21
### Updated
- Requirements

## [1.1.16] - 2020-06-20
### Fixed
- Services config update error

## [1.1.15] - 2020-06-07
### Updated
- Handle non trading exchanges

## [1.1.14] - 2020-06-02
### Added
- Web login

## [1.1.13] - 2020-05-27
### Update
- Cython version

## [1.1.12] - 2020-05-26
### Updated
- Requirements

## [1.1.11] - 2020-05-21
### Updated
- Remove advanced manager from commons

## [1.1.10] - 2020-05-19
### Added
- Config constants

## [1.1.9] - 2020-05-19
### Added
- OctoBot channels initialization

## [1.1.8] - 2020-05-18
### Added
- run_in_bot_async_executor util function

## [1.1.7] - 2020-05-17
### Fixed
- Bot interface config command

## [1.1.6] - 2020-05-16
### Updated
- Requirements

## [1.1.5] - 2020-05-15
### Updated
- OctoBot requirements

## [1.1.4] - 2020-05-10
### Updated
- Stop interface
- Telegram requirement

## [1.1.3] - 2020-05-10
### Updated
- Channel requirement
- Commons requirement
- Trading requirement

## [1.1.2] - 2020-05-06
### Added
- [Service] Webhook

## [1.1.1] - 2020-05-03
### Added
- Can now edit user config in services

## [1.1.0] - 2020-05-02
### Updated
- Octobot backtesting import paths

## [1.0.8] - 2020-05-01
### Added
- Include interfaces and notifications

## [1.0.7] - 2020-05-01
### Updated
- Handle multiple services for service feeds and interfaces

## [1.0.6] - 2020-04-17
### Updated
- python-telegram-bot requirement

## [1.0.5] - 2020-04-13
### Added
- ENV_WEB_ADDRESS environment constant

## [1.0.4] - 2020-04-13
### Added
- WEB_PORT environment constant

## [1.0.3] - 2020-04-10
### Added
- get_backtesting_service_feed api
- Service feed handling

## [1.0.2] - 2020-04-04
### Update
- Requirements version

### Fixed
- Travis CI file

## [1.0.1] - 2020-11-02
### Added
- Version update

## [1.0.0] - 2020-01-02
### Added
- Services
- Service-feeds
