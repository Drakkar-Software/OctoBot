import typing

import octobot_copy.copiers.account_copier as account_copier
import octobot_copy.copiers.futures_account_copier as futures_account_copier
import octobot_copy.copiers.option_account_copier as option_account_copier
import octobot_copy.copiers.spot_account_copier as spot_account_copier
import octobot_copy.entities as copy_entities
import octobot_copy.exchange as copy_exchange

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges
    import octobot_trading.modes


def create_account_copier(
    reference_account: copy_entities.Account,
    copy_settings: copy_entities.AccountCopySettings,
    copier_exchange_manager: "octobot_trading.exchanges.ExchangeManager",
    copier_trading_mode: typing.Optional["octobot_trading.modes.AbstractTradingMode"] = None,
) -> account_copier.AccountCopier:
    """
    Build an ExchangeInterface from copier_exchange_manager and return the AccountCopier implementation
    suited to that copier_exchange_manager (option, future, or spot) .
    """
    copier_exchange_interface = copy_exchange.ExchangeInterface(
        copier_exchange_manager, copier_trading_mode
    )
    if copier_exchange_manager.is_option:
        return option_account_copier.OptionAccountCopier(
            reference_account,
            copier_exchange_interface,
            copy_settings,
        )
    if copier_exchange_manager.is_future:
        return futures_account_copier.FuturesAccountCopier(
            reference_account,
            copier_exchange_interface,
            copy_settings,
        )
    return spot_account_copier.SpotAccountCopier(
        reference_account,
        copier_exchange_interface,
        copy_settings,
    )
