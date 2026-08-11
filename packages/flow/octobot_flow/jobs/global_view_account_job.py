#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import octobot_protocol.models as protocol_models
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.exchanges.util.exchange_data as exchange_data_module
import octobot_trading.util.protocol_trading_mapping as protocol_trading_mapping

import octobot_flow.entities
import octobot_flow.errors
import octobot_flow.logic.accounts.account_state_persistence as account_state_persistence_module
import octobot_flow.logic.configuration.profile_data_factory as profile_data_factory_module
import octobot_flow.logic.exchange.simulator.simulated_order_fill_detector as simulated_order_fill_detector_module
import octobot_flow.logic.exchange.simulator.simulated_portfolio_seeder as simulated_portfolio_seeder_module
import octobot_flow.logic.global_view.account_refresh_builder as account_refresh_builder_module
import octobot_flow.logic.global_view.exchange_account_refresh as exchange_account_refresh_module
import octobot_flow.logic.global_view.global_view_persistence as global_view_persistence_module


class GlobalViewAccountJob:
    def __init__(self, user_id: str, context: octobot_flow.entities.GlobalViewAccountContext):
        self.user_id = user_id
        self.context = context

    async def run(self) -> octobot_flow.entities.GlobalViewAccountRefreshResult:
        account = self.context.account
        account_specifics = account.specifics
        if account_specifics is None or account_specifics.actual_instance is None:
            raise octobot_flow.errors.GlobalViewUnsupportedAccountError(
                "Account.specifics.actual_instance is required for global view refresh."
            )
        account_specifics_instance = account_specifics.actual_instance
        if isinstance(account_specifics_instance, protocol_models.GenericAccount):
            return octobot_flow.entities.GlobalViewAccountRefreshResult(
                updated_account=account,
                changed_order_ids=set(),
            )
        if isinstance(account_specifics_instance, protocol_models.BlockchainAccount):
            raise octobot_flow.errors.GlobalViewUnsupportedAccountError(
                "Blockchain accounts are not supported yet."
            )
        if not isinstance(account_specifics_instance, protocol_models.ExchangeAccount):
            raise octobot_flow.errors.GlobalViewUnsupportedAccountError(
                f"Unsupported account specifics type: {type(account_specifics_instance).__name__}."
            )

        previous_open_order_exchange_ids = account_state_persistence_module.load_previous_open_order_exchange_ids(
            self.user_id,
            account.id,
        )
        previous_open_orders = account_state_persistence_module.load_previous_open_orders(
            self.user_id,
            account.id,
        )
        persist_open_orders = (
            not self.context.has_bound_automation
            and bool(previous_open_orders)
        )
        profile_data = profile_data_factory_module.profile_data_for_account(
            account,
            self.context.exchange_account,
            self.context.exchange_config,
            self.context.trading_type,
            is_simulated=account.is_simulated,
        )
        exchange_data = exchange_data_module.exchange_data_factory(
            exchange_internal_name=self.context.exchange_config.exchange,
            exchange_type=protocol_trading_mapping.TRADING_TYPE_TO_EXCHANGE_TYPE.get(self.context.trading_type).value,
            sandboxed=self.context.exchange_config.sandboxed,
            auth_details=self.context.auth_details,
        )
        tentacles_setup_config = tentacles_manager_api.get_full_tentacles_setup_config()
        async with trading_exchanges.exchange_manager_from_exchange_data(
            exchange_data,
            profile_data,
            tentacles_setup_config,
            price_fallback=None,
        ) as exchange_manager:
            if account.is_simulated:
                simulated_portfolio_seeder_module.seed_simulated_portfolio(exchange_manager, account)
                exchange_refresh_result = await exchange_account_refresh_module.refresh_exchange_account(
                    exchange_manager,
                    self.context.trading_type,
                    previous_open_order_exchange_ids,
                    is_simulated=True,
                    previous_open_orders=previous_open_orders,
                )
            else:
                open_order_symbols = simulated_order_fill_detector_module.symbols_from_open_orders(
                    previous_open_orders,
                )
                exchange_refresh_result = await exchange_account_refresh_module.refresh_exchange_account(
                    exchange_manager,
                    self.context.trading_type,
                    previous_open_order_exchange_ids,
                    fetch_open_orders=bool(open_order_symbols),
                    open_order_symbols=open_order_symbols,
                )

        refresh_result = account_refresh_builder_module.build_global_view_account_refresh_result(
            self.user_id,
            self.context,
            exchange_refresh_result,
        )
        global_view_persistence_module.persist_global_view_refresh_result(
            self.user_id,
            account.id,
            refresh_result,
            persist_open_orders=persist_open_orders,
        )
        return refresh_result
