import octobot_commons.configuration.fields_utils as fields_utils
import octobot_commons.constants as commons_constants
import octobot_commons.profiles.profile_data as commons_profile_data
import octobot_commons.timestamp_util as timestamp_util
import octobot_protocol.models as protocol_models
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.exchanges.util.exchange_data as exchange_data_module
import octobot_trading.util.protocol_trading_mapping as protocol_trading_mapping

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.util.account_authentication_resolver as account_authentication_resolver
import octobot_node.scheduler.user_actions.user_actions_executor.util.exchange_account_resolver as exchange_account_resolver


async def _fetch_api_key_rights(exchange) -> list[trading_enums.APIKeyRights]:
    try:
        return await exchange.get_permissions()
    except trading_errors.NotSupported:
        return list(protocol_trading_mapping.OPTIMISTIC_API_KEY_RIGHTS_WHEN_PERMISSIONS_UNSUPPORTED)


def _account_permissions_from_api_key_rights(
    api_key_rights: list[trading_enums.APIKeyRights],
) -> list[protocol_models.AccountPermission]:
    return [
        account_permission
        for api_key_right in api_key_rights
        if (
            account_permission := protocol_trading_mapping.API_KEY_RIGHT_TO_ACCOUNT_PERMISSION.get(api_key_right)
        ) is not None
    ]


def _validate_account_api_key_rights(api_key_rights: list[trading_enums.APIKeyRights]) -> None:
    if not api_key_rights:
        raise trading_errors.InvalidAPIKeyPermissionsError("No permissions found")
    if trading_enums.APIKeyRights.READING not in api_key_rights:
        raise trading_errors.InvalidAPIKeyPermissionsError("READING permission is required")
    if (
        trading_enums.APIKeyRights.WITHDRAWALS in api_key_rights
        and not trading_constants.ALLOW_FUNDS_TRANSFER
    ):
        raise trading_errors.InvalidAPIKeyPermissionsError(
            "WITHDRAWALS permission found, but funds transfer is disabled. "
            "Please remove the permission or enable funds transfer."
        )


async def update_account_state(
    account: protocol_models.Account,
    user_id: str,
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
        user_id,
    )
    account_updates: dict = {"state": checked_state}
    if assets is not None:
        account_updates["assets"] = assets
    account_updates["updated_at"] = timestamp_util.utc_now_datetime()
    return account.model_copy(update=account_updates)


def _encrypted_exchange_auth_details(
    exchange_account: protocol_models.ExchangeAccount,
    authentication: protocol_models.AccountAuthentication | None,
    trading_type: protocol_models.TradingType,
    sandboxed: bool,
) -> exchange_data_module.ExchangeAuthDetails:
    if authentication is None:
        return exchange_data_module.ExchangeAuthDetails(
            exchange_type=protocol_trading_mapping.TRADING_TYPE_TO_EXCHANGE_TYPE.get(trading_type).value,
            sandboxed=sandboxed,
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
        exchange_type=protocol_trading_mapping.TRADING_TYPE_TO_EXCHANGE_TYPE.get(trading_type).value,
        sandboxed=sandboxed,
        exchange_account_id=exchange_account.remote_account_id,
    )


def _trading_type_for_account_state_check(
    account: protocol_models.Account,
) -> protocol_models.TradingType:
    account_assets = account.assets
    if not account_assets:
        return protocol_models.TradingType.SPOT
    trading_types = {
        assets_for_trading_type.trading_type
        for assets_for_trading_type in account_assets
    }
    if len(trading_types) > 1:
        trading_type_names = sorted(trading_type.value for trading_type in trading_types)
        raise node_errors.AmbiguousTradingTypeError(
            f"Account.assets maps to multiple trading types: {', '.join(trading_type_names)}."
        )
    return next(iter(trading_types))


async def _check_exchange_account_state(
    exchange_account: protocol_models.ExchangeAccount,
    account: protocol_models.Account,
    user_id: str,
) -> tuple[protocol_models.AccountState, list[protocol_models.DetailedAssetsForTradingType] | None]:
    if account.is_simulated:
        return (
            protocol_models.AccountState(
                status=protocol_models.AccountStatus.VALID,
                message=protocol_models.AccountStatusMessage.VALID,
            ),
            None, # not fetching assets for simulated accounts
        )
    authentication = account_authentication_resolver.get_exchange_authentication(
        user_id,
        account,
    )
    exchange_config = exchange_account_resolver.get_exchange_config(
        user_id,
        exchange_account,
    )
    trading_type = _trading_type_for_account_state_check(account)
    profile_data = commons_profile_data.ProfileData(
        exchanges=[
            commons_profile_data.ExchangeData(
                internal_name=exchange_config.exchange,
                exchange_type=protocol_trading_mapping.TRADING_TYPE_TO_EXCHANGE_TYPE.get(trading_type).value,
                exchange_account_id=exchange_account.remote_account_id,
                sandboxed=exchange_config.sandboxed,
            )
        ]
    )
    profile_data.trader.enabled = True
    exchange_data = exchange_data_module.exchange_data_factory(
        exchange_internal_name=exchange_config.exchange,
        exchange_type=protocol_trading_mapping.TRADING_TYPE_TO_EXCHANGE_TYPE.get(trading_type).value,
        sandboxed=exchange_config.sandboxed,
        auth_details=_encrypted_exchange_auth_details(
            exchange_account,
            authentication,
            trading_type,
            exchange_config.sandboxed,
        ),
    )
    tentacles_setup_config = tentacles_manager_api.get_full_tentacles_setup_config()
    try:
        async with trading_exchanges.exchange_manager_from_exchange_data(
            exchange_data,
            profile_data,
            tentacles_setup_config,
            price_fallback=None,
        ) as exchange_manager:
            return await _check_exchange_manager_state(exchange_manager, account)
    except Exception as error:
        return _account_check_failure_result(error)


async def _check_exchange_manager_state(
    exchange_manager,
    account: protocol_models.Account,
) -> tuple[protocol_models.AccountState, list[protocol_models.DetailedAssetsForTradingType] | None]:
    permissions: list[protocol_models.AccountPermission] | None = None
    try:
        balance = await exchange_manager.exchange.get_balance()
        api_key_rights = await _fetch_api_key_rights(exchange_manager.exchange)
        permissions = _account_permissions_from_api_key_rights(api_key_rights)
        _validate_account_api_key_rights(api_key_rights)
        assets = _assets_from_balance(balance, _trading_type_for_account_state_check(account))
        return (
            protocol_models.AccountState(
                status=protocol_models.AccountStatus.VALID,
                message=protocol_models.AccountStatusMessage.VALID,
                permissions=permissions,
            ),
            assets,
        )
    except Exception as error:
        return _account_check_failure_result(error, permissions=permissions)


def _account_check_failure_result(
    error: BaseException,
    *,
    permissions: list[protocol_models.AccountPermission] | None = None,
) -> tuple[protocol_models.AccountState, None]:
    if isinstance(error, trading_errors.RetriableFailedRequest):
        raise error
    if isinstance(error, trading_errors.InvalidAPIKeyIPWhitelistError):
        return _invalid_state(protocol_models.AccountStatusMessage.INVALID_API_IP_WHITELIST), None
    if isinstance(error, trading_errors.InvalidAPIKeyPermissionsError):
        return _invalid_state_from_permissions_error(permissions), None
    if isinstance(error, trading_errors.AuthenticationError):
        return _invalid_state(
            protocol_models.AccountStatusMessage.INVALID_API_KEYS,
            permissions=[],
        ), None
    return _invalid_state(
        protocol_models.AccountStatusMessage.INTERNAL_SERVER_ERROR,
        permissions=permissions,
    ), None


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


def _assets_from_balance(
    balance: dict,
    trading_type: protocol_models.TradingType,
) -> list[protocol_models.DetailedAssetsForTradingType]:
    detailed_assets = [
        protocol_models.DetailedAsset(
            symbol=holding_symbol,
            total=total_amount,
            available=available_amount,
        )
        for holding_symbol, total_amount, available_amount in _balance_currency_holdings(balance)
    ]
    if not detailed_assets:
        return []
    return [
        protocol_models.DetailedAssetsForTradingType(
            trading_type=trading_type,
            assets=detailed_assets,
        )
    ]


def _invalid_state(
    status_message: protocol_models.AccountStatusMessage,
    *,
    permissions: list[protocol_models.AccountPermission] | None = None,
) -> protocol_models.AccountState:
    return protocol_models.AccountState(
        status=protocol_models.AccountStatus.INVALID,
        message=status_message,
        permissions=permissions,
    )


def _invalid_state_from_permissions_error(
    permissions: list[protocol_models.AccountPermission] | None,
) -> protocol_models.AccountState:
    if (
        permissions is not None
        and protocol_models.AccountPermission.WITHDRAW in permissions
        and not trading_constants.ALLOW_FUNDS_TRANSFER
    ):
        status_message = protocol_models.AccountStatusMessage.REVOKE_API_WITHDRAWAL_RIGHTS
    else:
        status_message = protocol_models.AccountStatusMessage.INVALID_API_KEYS
    return _invalid_state(status_message, permissions=permissions or [])
