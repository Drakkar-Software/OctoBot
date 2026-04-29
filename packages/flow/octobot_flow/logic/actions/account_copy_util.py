import decimal
import time

import octobot_commons.constants as common_constants
import octobot_commons.dsl_interpreter
import octobot_commons.profiles as commons_profiles
import octobot_commons.symbols as symbol_util
import octobot_commons.logging as logging

import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities

import octobot_flow.constants
import octobot_flow.entities
import octobot_flow.errors
import octobot_flow.logic.actions.actions_factory as actions_factory
import octobot_flow.logic.dsl as dsl_logic

import tentacles.Meta.DSL_operators.exchange_operators as exchange_operators


def update_action_trading_signal_if_relevant(
    action: octobot_flow.entities.AbstractActionDetails,
    trading_signal: octobot_flow.entities.TradingSignal,
    default_reference_market: str,
) -> None:
    if not isinstance(action, octobot_flow.entities.DSLScriptActionDetails):
        return
    dsl_script = action.dsl_script
    if dsl_script is None or not str(dsl_script).strip():
        raise octobot_flow.errors.InvalidAutomationActionError(
            "DSL script is required to update trading signal on a DSL action"
        )
    dsl_script_str = str(dsl_script)
    if common_constants.UNRESOLVED_PARAMETER_PLACEHOLDER in dsl_script_str:
        raise octobot_flow.errors.UnresolvedDSLScriptError(
            "DSL script has unresolved parameters; resolve dependencies before applying trading signals"
        )
    dsl_executor = dsl_logic.DSLExecutor(
        commons_profiles.ProfileData(),
        None,
        dsl_script_str,
    )
    top = dsl_executor.get_top_operator()
    if not isinstance(top, octobot_commons.dsl_interpreter.Operator):
        return
    if top.get_name() not in (
        exchange_operators.CopyExchangeAccountOperatorNames.COPY_EXCHANGE_ACCOUNT.value,
    ):
        return
    params = top.get_computed_value_by_parameter()
    dsl_strategy_id = str(params["strategy_id"])
    if dsl_strategy_id != str(trading_signal.strategy_id):
        raise octobot_flow.errors.CommunityTradingSignalError(
            f"Trading signal strategy_id {trading_signal.strategy_id!r} does not match "
            f"copy_exchange_account strategy_id {dsl_strategy_id!r}"
        )
    account_copy_settings = copy_entities.parse_account_copy_settings(
        params.get("account_copy_settings")
    )
    reference_market = str(params["reference_market"]) or default_reference_market
    new_details = actions_factory.create_copy_exchange_account_action(
        params["strategy_id"], # type: ignore
        reference_market,
        trading_signal.account,
        account_copy_settings,
    )
    action.dsl_script = new_details.dsl_script
    action.resolved_dsl_script = new_details.resolved_dsl_script


def update_trading_signals(
    actions: list[octobot_flow.entities.AbstractActionDetails],
    trading_signals: list[octobot_flow.entities.TradingSignal],
    default_reference_market: str,
) -> None:
    for trading_signal in trading_signals:
        for action in actions:
            try:
                update_action_trading_signal_if_relevant(
                    action, trading_signal, default_reference_market
                )
            except octobot_flow.errors.CommunityTradingSignalError:
                # Signal applies to a different strategy than this copy_exchange_account action.
                continue


def reference_exchange_elements_to_account(
    elements: octobot_flow.entities.ExchangeAccountElements,
    fetched_exchange_data: octobot_flow.entities.FetchedExchangeData,
    reference_market: str,
) -> copy_entities.Account:
    content: dict[str, dict[str, decimal.Decimal]] = {}
    value_by_asset = {}
    zero_value = decimal.Decimal("0")
    for asset, values in elements.portfolio.content.items():
        content[asset] = {
            key: decimal.Decimal(str(amount)) for key, amount in values.items()
        }
        if asset == reference_market:
            value_by_asset[asset] = decimal.Decimal(str(values[common_constants.PORTFOLIO_TOTAL]))
        else:
            asset_value = zero_value
            try:
                if price := fetched_exchange_data.get_last_price(
                    symbol_util.merge_currencies(asset, reference_market)
                ):
                    asset_value = decimal.Decimal(str(values[common_constants.PORTFOLIO_TOTAL])) * price
                else:
                    logging.get_logger("account_copy_util").error(
                        f"No ticker price found for {symbol_util.merge_currencies(asset, reference_market)}. "
                        f"Portfolio ratios will be inaccurate."
                    )
            except KeyError as err:
                logging.get_logger("account_copy_util").error(
                    f"Impossible to evaluate {symbol_util.merge_currencies(asset, reference_market)} price: "
                    f"no fetched ticker price ({err})"
                )
            value_by_asset[asset] = asset_value
    total_value = sum(value_by_asset.values())
    for asset, values in elements.portfolio.content.items():
        if total_value == zero_value:
            content[asset][copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO] = zero_value
        else:
            content[asset][copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO] = value_by_asset[asset] / total_value
    return copy_entities.Account(
        updated_at=time.time(),
        content=content,
        orders=elements.orders.open_orders
    )


def create_account_copy_settings(
    automation: octobot_flow.entities.AutomationDetails,
) -> copy_entities.AccountCopySettings:
    grace_seconds = octobot_flow.constants.DEFAULT_COPY_TRADING_ORPHAN_CANCEL_GRACE_SECONDS
    threshold = octobot_flow.constants.DEFAULT_COPY_TRADING_ORPHAN_GRACE_ABORT_THRESHOLD
    missed_signals_threshold = octobot_flow.constants.DEFAULT_COPY_TRADING_MISSED_SIGNALS_GRACE_ABORT_THRESHOLD
    return copy_entities.AccountCopySettings(
        mirrored_orphan_cancel_grace_seconds=grace_seconds,
        mirrored_orphan_grace_abort_threshold=threshold,
        missed_signals_grace_abort_threshold=missed_signals_threshold,
        mirrored_orphan_grace_pair_ratio_max_delta=(
            octobot_flow.constants.DEFAULT_COPY_TRADING_ORPHAN_GRACE_PAIR_RATIO_MAX_DELTA
        ),
    )
