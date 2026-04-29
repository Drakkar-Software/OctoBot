# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.43] - 2026-01-14
### Update
[LBank] add api key permissions check

## [1.2.42] - 2025-09-04
### Update
[Binance] include transfer permissions in withdrawal rights

## [1.2.41] - 2025-08-08
### Added
[Coinbase] set id

## [1.2.40] - 2025-06-26
### Fixed
[Proxy] handle all aiohttp proxy errors

## [1.2.39] - 2025-06-09
### Updated
- [Errors] add NetworkError

## [1.2.38] - 2025-04-07
### Updated
- [BitMart] add _get_api_key_rights
- 
## [1.2.37] - 2025-02-22
### Updated
- [Coinex] add _get_api_key_rights

## [1.2.36] - 2025-02-03
### Updated
- [Exchanges] handle aiohttp_socks ProxyConnectionError

## [1.2.35] - 2025-01-31
### Updated
- [Exchanges] use more accurate errors

## [1.2.34] - 2025-01-27
### Updated
- [Exchanges] handle proxy errors 

## [1.2.33] - 2025-01-22
### Updated
- [Binance] fix binance futures check 

## [1.2.32] - 2025-01-11
### Updated
- [MEXC] add _get_api_key_rights

## [1.2.31] - 2025-01-09
### Updated
- [Binance] handle futures trading rights

## [1.2.30] - 2024-12-02
### Updated
- [Binance] handle sandbox

## [1.2.29] - 2024-10-02
### Added
- log on invalid creds

## [1.2.28] - 2024-09-18
### Added
- [HollaEx]

## [1.2.27] - 2024-08-20
### Added
- [BitMart]

## [1.2.26] - 2024-07-25
### Fixed
- [Binance] Fix crash on account check with invalid API key format

## [1.2.25] - 2024-07-05
### Updated
- [CCXT] update to ccxt 4.3.56

## [1.2.24] - 2024-06-16
### Updated
- Exchanges: fix api key format errors

## [1.2.23] - 2024-06-06
### Updated
- Exchanges: is_api_permission_error api

## [1.2.22] - 2024-05-10
### Fixed
- Coinbase: handle UnexpectedDER error

## [1.2.21] - 2024-05-10
### Fixed
- Coinbase: missing trading permission check

## [1.2.20] - 2024-05-01
### Fixed
- Coinbase: handle removed /v2/user/auth endpoint

## [1.2.19] - 2024-04-17
### Fixed
- Coinbase: handle other invalid API key format

## [1.2.18] - 2024-04-16
### Fixed
- Coinbase: handle invalid API key format

## [1.2.17] - 2024-04-15
### Updated
- CCXT to 4.2.95

## [1.2.16] - 2024-04-13
### Fixed
- BinanceUS api rights checks

## [1.2.15] - 2024-04-02
### Added
- BinanceUS & Coinbase

## [1.2.14] - 2024-01-24
### Added
- Bingx _get_api_key_rights

## [1.2.13] - 2024-01-18
### Added
- CoinEx

## [1.2.12] - 2024-01-08
### Updated
- update for CCXT 4.2.10

## [1.2.11] - 2023-12-10
### Added
- Bingx
### Updated
- update for CCXT 4.1.82

## [1.2.10] - 2023-12-06
### Updated
- update for CCXT 4.1.77

## [1.2.9] - 2023-08-23
### Added
- Kucoin & OKX api key right check

## [1.2.8] - 2023-08-13
### Added
- withdrawal right check in api keys

## [1.2.7] - 2023-08-11
### Added
- Binance api key permission checks

## [1.2.6] - 2023-07-29
### Fixed
- Binance support check

## [1.2.5] - 2023-06-29
### Added
- Crypto.com
- MEXC

## [1.2.4] - 2023-06-24
### Added
- Kucoin and Kucoin futures

## [1.2.3] - 2023-05-02
### Updated
- setup.py

## [1.2.2] - 2023-05-02
### Remove
- Constants

## [1.2.1] - 2023-05-02
### Added
- Constants

## [1.2.0] - 2023-05-02
### Updated
- Supported python versions

## [1.0.19] - 2022-02-12
### Added
- Stop method

## [1.0.18] - 2022-01-17
### Updated
- Bitget handling

## [1.0.17] - 2022-10-12
### Added
- Exchange initialize
- Binance legacy ids management
### Updated
- Binance broker id
### Removed
- FTX

## [1.0.16] - 2022-10-12
### Updated
- CCXT version

## [1.0.15] - 2022-09-24
### Added
- Phemex

## [1.0.14] - 2022-08-07
### Added
- Bitget

## [1.0.13] - 2022-06-05
### Updated
- Renamed OKEx into OKX

## [1.0.12] - 2021-10-27
### Added
- Bybit spot and future
- Ascendex

### Fixed 
- OKEx tests

## [1.0.11] - 2021-08-31
### Added
- Huobi pro

## [1.0.10] - 2021-08-27
### Added
- Huobi ids

## [1.0.9] - 2021-08-25
### Added
- GateIO ids

## [1.0.8] - 2021-08-15
### Updated
- Binance error messages

## [1.0.7] - 2021-08-08
### Fix
- Check credentials in all exchange is_valid_account()

## [1.0.6] - 2021-08-02
### Added
- FTX ids
- OKEx ids

## [1.0.5] - 2021-08-02
### Added
- Referral id

## [1.0.4] - 2021-07-12
### Fixed
- Binance client id generator

## [1.0.3] - 2021-07-08
### Added
- Account credentials check on is_valid_account
- ExchangeAuthError

## [1.0.2] - 2021-06-26
### Added
- TimeSyncError

## [1.0.1] - 2021-06-23
### Added
- Binance ids

## [1.0.0] - 2021-06-06
### Project creation
