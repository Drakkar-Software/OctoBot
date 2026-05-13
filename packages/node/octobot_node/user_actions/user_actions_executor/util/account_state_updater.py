import octobot_commons.configuration.fields_utils as fields_utils
import octobot_commons.profiles.profile_data as commons_profile_data
import octobot_protocol.models as protocol_models
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.exchanges.util.exchange_data as exchange_data_module

import octobot_node.errors as node_errors


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


async def _request_exchange_to_ensure_authentication(exchange_manager) -> None:
    await exchange_manager.exchange.request_exchange_to_ensure_authentication()


async def _ensure_api_key_permissions(exchange_manager) -> None:
    await exchange_manager.exchange.ensure_api_key_permissions()


async def update_account_state(
    account: protocol_models.Account,
) -> protocol_models.Account:
    account_details = account.details
    if account_details is None or account_details.actual_instance is None:
        raise node_errors.InvalidUserActionPayloadError(
            "Account.details.actual_instance is required for account checks."
        )
    account_details_instance = account_details.actual_instance
    if isinstance(account_details_instance, protocol_models.GenericAccount):
        return account
    if isinstance(account_details_instance, protocol_models.BlockchainAccount):
        raise node_errors.InvalidUserActionPayloadError("Blockchain accounts are not supported yet.")
    if not isinstance(account_details_instance, protocol_models.ExchangeAccount):
        raise node_errors.InvalidUserActionPayloadError(
            f"Unsupported account details type for checks: {type(account_details_instance).__name__}."
        )
    checked_state = await _check_exchange_account_state(account_details_instance)
    return account.model_copy(update={"state": checked_state})


def _encrypted_exchange_auth_details(
    exchange_account: protocol_models.ExchangeAccount,
) -> exchange_data_module.ExchangeAuthDetails:
    # Exchange manager expects Fernet-encrypted strings (see decrypt_element_if_possible on load).
    api_password = ""
    if exchange_account.api_passphrase:
        api_password = fields_utils.encrypt(exchange_account.api_passphrase).decode()
    return exchange_data_module.ExchangeAuthDetails(
        api_key=fields_utils.encrypt(exchange_account.api_key).decode(),
        api_secret=fields_utils.encrypt(exchange_account.api_secret).decode(),
        api_password=api_password,
        exchange_type=_exchange_type_from_trading_type(exchange_account.trading_type),
        sandboxed=False,
        exchange_account_id=exchange_account.remote_account_id,
    )


async def _check_exchange_account_state(
    exchange_account: protocol_models.ExchangeAccount,
) -> protocol_models.AccountState:
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
        auth_details=_encrypted_exchange_auth_details(exchange_account),
    )
    tentacles_setup_config = tentacles_manager_api.get_full_tentacles_setup_config()
    async with trading_exchanges.exchange_manager_from_exchange_data(
        exchange_data,
        profile_data,
        tentacles_setup_config,
        price_fallback=None,
    ) as exchange_manager:
        return await _check_exchange_manager_state(exchange_manager)


async def _check_exchange_manager_state(exchange_manager) -> protocol_models.AccountState:
    try:
        await _request_exchange_to_ensure_authentication(exchange_manager)
        await _ensure_api_key_permissions(exchange_manager)
        return protocol_models.AccountState(
            status=protocol_models.AccountStatus.VALID,
            message=protocol_models.AccountStatusMessage.VALID,
        )
    except trading_errors.RetriableFailedRequest:
        raise
    except trading_errors.InvalidAPIKeyIPWhitelistError:
        return _invalid_state(protocol_models.AccountStatusMessage.INVALID_API_IP_WHITELIST)
    except trading_errors.AuthenticationError as authentication_error:
        authentication_message = str(authentication_error).lower()
        if "withdrawal" in authentication_message:
            return _invalid_state(protocol_models.AccountStatusMessage.REVOKE_API_WITHDRAWAL_RIGHTS)
        if any(permission_keyword in authentication_message for permission_keyword in ("permission", "trading")):
            return _invalid_state(protocol_models.AccountStatusMessage.MISSING_API_TRADING_RIGHTS)
        return _invalid_state(protocol_models.AccountStatusMessage.INVALID_API_KEYS)
    except Exception:
        return _invalid_state(protocol_models.AccountStatusMessage.INTERNAL_SERVER_ERROR)


def _invalid_state(
    status_message: protocol_models.AccountStatusMessage,
) -> protocol_models.AccountState:
    return protocol_models.AccountState(
        status=protocol_models.AccountStatus.INVALID,
        message=status_message,
    )
