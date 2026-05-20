import octobot_commons.configuration.fields_utils as fields_utils
import octobot_commons.constants as commons_constants
import octobot_commons.profiles.profile_data as commons_profile_data
import octobot_protocol.models as protocol_models
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.exchanges.util.exchange_data as exchange_data_module

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.util.account_authentication_resolver as account_authentication_resolver


_TRADING_TYPE_TO_EXCHANGE_TYPE: dict[protocol_models.TradingType, trading_enums.ExchangeTypes] = {
    protocol_models.TradingType.SPOT: trading_enums.ExchangeTypes.SPOT,
    protocol_models.TradingType.FUTURES: trading_enums.ExchangeTypes.FUTURE,
    protocol_models.TradingType.OPTIONS: trading_enums.ExchangeTypes.OPTION,
    protocol_models.TradingType.MARGIN: trading_enums.ExchangeTypes.MARGIN,
}


def _exchange_type_from_trading_type(
    trading_type: protocol_models.TradingType,
) -> str:
    return _TRADING_TYPE_TO_EXCHANGE_TYPE[trading_type].value


async def _ensure_api_key_permissions(exchange_manager) -> None:
    await exchange_manager.exchange.ensure_api_key_permissions()


async def update_account_state(
    account: protocol_models.Account,
    wallet_address: str,
) -> protocol_models.Account:
    account_specifics = account.specifics
    if account_specifics is None or account_specifics.actual_instance is None:
        raise node_errors.InvalidUserActionPayloadError(
            "Account.specifics.actual_instance is required for account checks."
        )
    account_specifics_instance = account_specifics.actual_instance
    if isinstance(account_specifics_instance, protocol_models.GenericAccount):
        return account
    if isinstance(account_specifics_instance, protocol_models.BlockchainAccount):
        raise node_errors.InvalidUserActionPayloadError("Blockchain accounts are not supported yet.")
    if not isinstance(account_specifics_instance, protocol_models.ExchangeAccount):
        raise node_errors.InvalidUserActionPayloadError(
            f"Unsupported account specifics type for checks: {type(account_specifics_instance).__name__}."
        )
    checked_state, assets = await _check_exchange_account_state(
        account_specifics_instance,
        account,
        wallet_address,
    )
    account_updates: dict = {"state": checked_state}
    if assets is not None:
        account_updates["assets"] = assets
    return account.model_copy(update=account_updates)


def _encrypted_exchange_auth_details(
    exchange_account: protocol_models.ExchangeAccount,
    authentication: protocol_models.AccountAuthentication | None,
) -> exchange_data_module.ExchangeAuthDetails:
    if authentication is None:
        return exchange_data_module.ExchangeAuthDetails(
            exchange_type=_exchange_type_from_trading_type(exchange_account.trading_type),
            sandboxed=False,
            exchange_account_id=exchange_account.remote_account_id,
        )
    # Exchange manager expects Fernet-encrypted strings (see decrypt_element_if_possible on load).
    api_password = ""
    if authentication.api_passphrase:
        api_password = fields_utils.encrypt(authentication.api_passphrase).decode()
    return exchange_data_module.ExchangeAuthDetails(
        api_key=fields_utils.encrypt(authentication.api_key).decode(),
        api_secret=fields_utils.encrypt(authentication.api_secret).decode(),
        api_password=api_password,
        exchange_type=_exchange_type_from_trading_type(exchange_account.trading_type),
        sandboxed=False,
        exchange_account_id=exchange_account.remote_account_id,
    )


async def _check_exchange_account_state(
    exchange_account: protocol_models.ExchangeAccount,
    account: protocol_models.Account,
    wallet_address: str,
) -> tuple[protocol_models.AccountState, list[protocol_models.DetailedAsset] | None]:
    authentication = account_authentication_resolver.get_exchange_authentication(
        wallet_address,
        account,
    )
    profile_data = commons_profile_data.ProfileData(
        exchanges=[
            commons_profile_data.ExchangeData(
                internal_name=exchange_account.exchange,
                exchange_type=_exchange_type_from_trading_type(exchange_account.trading_type),
                exchange_account_id=exchange_account.remote_account_id,
                sandboxed=False,
            )
        ]
    )
    profile_data.trader.enabled = True
    exchange_data = exchange_data_module.exchange_data_factory(
        exchange_internal_name=exchange_account.exchange,
        exchange_type=_exchange_type_from_trading_type(exchange_account.trading_type),
        sandboxed=False,
        auth_details=_encrypted_exchange_auth_details(exchange_account, authentication),
    )
    tentacles_setup_config = tentacles_manager_api.get_full_tentacles_setup_config()
    async with trading_exchanges.exchange_manager_from_exchange_data(
        exchange_data,
        profile_data,
        tentacles_setup_config,
        price_fallback=None,
    ) as exchange_manager:
        return await _check_exchange_manager_state(exchange_manager, account)


async def _check_exchange_manager_state(
    exchange_manager,
    account: protocol_models.Account,
) -> tuple[protocol_models.AccountState, list[protocol_models.DetailedAsset] | None]:
    try:
        balance = await exchange_manager.exchange.get_balance()
        await _ensure_api_key_permissions(exchange_manager)
        assets = _assets_from_balance(balance)
        return (
            protocol_models.AccountState(
                status=protocol_models.AccountStatus.VALID,
                message=protocol_models.AccountStatusMessage.VALID,
            ),
            assets,
        )
    except trading_errors.RetriableFailedRequest:
        raise
    except trading_errors.InvalidAPIKeyIPWhitelistError:
        return _invalid_state(protocol_models.AccountStatusMessage.INVALID_API_IP_WHITELIST), None
    except trading_errors.AuthenticationError as authentication_error:
        authentication_message = str(authentication_error).lower()
        if "withdrawal" in authentication_message:
            return _invalid_state(protocol_models.AccountStatusMessage.REVOKE_API_WITHDRAWAL_RIGHTS), None
        if any(permission_keyword in authentication_message for permission_keyword in ("permission", "trading")):
            return _invalid_state(protocol_models.AccountStatusMessage.MISSING_API_TRADING_RIGHTS), None
        return _invalid_state(protocol_models.AccountStatusMessage.INVALID_API_KEYS), None
    except Exception:
        return _invalid_state(protocol_models.AccountStatusMessage.INTERNAL_SERVER_ERROR), None


def _balance_currency_holdings(balance: dict) -> list[tuple[str, float, float]]:
    holdings: list[tuple[str, float, float]] = []
    for symbol, amounts in balance.items():
        if not isinstance(amounts, dict):
            continue
        total_amount = float(amounts.get(commons_constants.PORTFOLIO_TOTAL) or 0)
        if total_amount == 0:
            continue
        available_amount = float(
            amounts.get(commons_constants.PORTFOLIO_AVAILABLE)
            or amounts.get("free")
            or 0
        )
        holdings.append((str(symbol), total_amount, available_amount))
    return holdings


def _assets_from_balance(balance: dict) -> list[protocol_models.DetailedAsset]:
    return [
        protocol_models.DetailedAsset(
            symbol=holding_symbol,
            total=total_amount,
            available=available_amount,
        )
        for holding_symbol, total_amount, available_amount in _balance_currency_holdings(balance)
    ]


def _invalid_state(
    status_message: protocol_models.AccountStatusMessage,
) -> protocol_models.AccountState:
    return protocol_models.AccountState(
        status=protocol_models.AccountStatus.INVALID,
        message=status_message,
    )
