#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import uuid
import typing

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

import octobot_node.models
import octobot.community.authentication as community_auth
import octobot.community.wallet_backend as wallet_backend

from .auth_errors import (
    AuthErrorCode,
    auth_http_exception,
    node_not_configured_exception,
)
try:
    from tentacles.Services.Interfaces.node_api_interface.api.rate_limits.login import (
        get_login_rate_limiter,
        login_client_ip,
    )
    from tentacles.Services.Interfaces.node_api_interface.core.http_rate_limit import (
        run_with_failure_rate_limit,
    )
except ImportError:
    from api.rate_limits.login import get_login_rate_limiter, login_client_ip  # type: ignore[no-redef]
    from core.http_rate_limit import run_with_failure_rate_limit  # type: ignore[no-redef]

security_basic = HTTPBasic(auto_error=False)

_LOGIN_COUNTABLE_FAILURE_CODES = frozenset(
    {
        AuthErrorCode.AUTH_INVALID_PASSPHRASE,
        AuthErrorCode.AUTH_WALLET_NOT_FOUND,
    }
)


def _should_count_login_failure(err: HTTPException) -> bool:
    if err.status_code != status.HTTP_401_UNAUTHORIZED:
        return False
    detail = err.detail
    if not isinstance(detail, dict):
        return False
    raw_code = detail.get("code")
    if raw_code is None:
        return False
    try:
        auth_code = AuthErrorCode(raw_code)
    except ValueError:
        return False
    return auth_code in _LOGIN_COUNTABLE_FAILURE_CODES


def _login_failure_counts_toward_limit(err: BaseException) -> bool:
    if not isinstance(err, HTTPException):
        return False
    return _should_count_login_failure(err)


def _user_from_wallet_credentials(
    auth: community_auth.CommunityAuthentication,
    credentials: HTTPBasicCredentials,
) -> octobot_node.models.User:
    wallet_address = credentials.username.lower()
    passphrase = credentials.password

    try:
        wallet_info = auth.authenticate_wallet(wallet_address, passphrase)
    except wallet_backend.WalletNotFoundError:
        raise auth_http_exception(
            status.HTTP_401_UNAUTHORIZED,
            AuthErrorCode.AUTH_WALLET_NOT_FOUND,
            message="Wallet address is not configured on this node",
        )
    except wallet_backend.InvalidPassphraseError:
        raise auth_http_exception(
            status.HTTP_401_UNAUTHORIZED,
            AuthErrorCode.AUTH_INVALID_PASSPHRASE,
            message="Passphrase verification failed",
        )
    except wallet_backend.WalletError as err:
        raise auth_http_exception(
            status.HTTP_401_UNAUTHORIZED,
            AuthErrorCode.AUTH_INVALID_PASSPHRASE,
            message=str(err),
        )

    auth.init_sync_client_for_wallet(wallet_address)

    return octobot_node.models.User(
        id=uuid.uuid5(uuid.NAMESPACE_URL, wallet_address),
        email=wallet_address,
        is_active=True,
        is_superuser=wallet_info.is_admin,
        full_name=wallet_info.name,
    )


def get_current_user(
    credentials: typing.Annotated[typing.Optional[HTTPBasicCredentials], Depends(security_basic)],
) -> octobot_node.models.User:
    auth = community_auth.CommunityAuthentication.instance()
    if auth is None:
        raise node_not_configured_exception()

    # Multi-wallet path: username = wallet address, password = passphrase
    if credentials is None or not credentials.username:
        # Check whether the node is configured at all (no credentials → can't auth anyway)
        if not auth.list_wallets():
            raise node_not_configured_exception()
        raise auth_http_exception(
            status.HTTP_401_UNAUTHORIZED,
            AuthErrorCode.AUTH_WALLET_ADDRESS_REQUIRED,
            message="Wallet address required as username",
        )

    passphrase = credentials.password
    if not passphrase:
        raise auth_http_exception(
            status.HTTP_401_UNAUTHORIZED,
            AuthErrorCode.AUTH_PASSPHRASE_REQUIRED,
            message="Passphrase required",
        )

    return _user_from_wallet_credentials(auth, credentials)


def get_login_rate_limited_user(
    request: Request,
    credentials: typing.Annotated[typing.Optional[HTTPBasicCredentials], Depends(security_basic)],
) -> octobot_node.models.User:
    """Wallet login with in-process rate limit (see api/rate_limits/login.py)."""
    client_ip = login_client_ip(request)
    return run_with_failure_rate_limit(
        get_login_rate_limiter(),
        dimensions={"client_ip": client_ip},
        action=lambda: get_current_user(credentials),
        should_record_failure=_login_failure_counts_toward_limit,
    )


# Route parameter aliases: Annotated[User, Depends(fn)] gives static type User and tells
# FastAPI to run fn before the handler. A plain `user: User` annotation would not inject auth.
CurrentUser = typing.Annotated[octobot_node.models.User, Depends(get_current_user)]
# Same as CurrentUser, but only for GET /login/test — counts failed passphrases per client IP.
LoginRateLimitedUser = typing.Annotated[
    octobot_node.models.User,
    Depends(get_login_rate_limited_user),
]


def get_optional_current_user(
    credentials: typing.Annotated[typing.Optional[HTTPBasicCredentials], Depends(security_basic)],
) -> typing.Optional[octobot_node.models.User]:
    if credentials is None or not credentials.username or not credentials.password:
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None


OptionalCurrentUser = typing.Annotated[typing.Optional[octobot_node.models.User], Depends(get_optional_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> octobot_node.models.User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user


AdminUser = typing.Annotated[octobot_node.models.User, Depends(get_current_active_superuser)]
