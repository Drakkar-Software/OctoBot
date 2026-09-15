import mock

import octobot_commons.dsl_interpreter
import octobot_commons.profiles as commons_profiles
import octobot_trading.enums as octobot_trading_enums_import
import octobot_trading.exchanges.util.exchange_data as exchange_data_import

import octobot_flow.entities as octobot_flow_entities
import octobot_flow.enums as octobot_flow_enums_import
import octobot_flow.logic.actions.actions_executor as actions_executor_import


def _trade_stub(trade_id: str) -> dict:
    trade_id_key = octobot_trading_enums_import.ExchangeConstantsOrderColumns.EXCHANGE_TRADE_ID.value
    return {trade_id_key: trade_id}


def _tx_stub(txid: str) -> dict:
    txid_key = octobot_trading_enums_import.ExchangeConstantsTransactionColumns.TXID.value
    return {txid_key: txid}


class TestSyncAfterExecutionWithManagerAndSnapshots:
    def test_applies_snapshots_without_conflict_when_exchange_manager_set(self):
        automation = octobot_flow_entities.AutomationDetails(
            metadata=octobot_flow_entities.AutomationMetadata(automation_id="aid"),
            exchange_account_elements=octobot_flow_entities.ExchangeAccountElements(),
        )
        executor_action = actions_executor_import.ActionsExecutor(
            None,
            mock.Mock(name="exchange_manager"),
            commons_profiles.ProfileData(),
            automation,
            [],
            False,
        )
        snap = octobot_flow_entities.ExchangeAccountElements(
            orders=exchange_data_import.OrdersDetails(open_orders=[{"id": "from-snap"}]),
        )
        executor_action._sync_after_execution([snap])
        assert automation.exchange_account_elements.orders.open_orders == [{"id": "from-snap"}]


class TestMergeSynchronizedSnapshotsUpsertsTradesAndUsesLastOrders:
    def test_merges_trades_and_orders(self):
        snap1 = octobot_flow_entities.ExchangeAccountElements(
            orders=exchange_data_import.OrdersDetails(open_orders=[{"id": "keep"}]),
            trades=[_trade_stub("t-first")],
            positions=[exchange_data_import.PositionDetails()],
        )
        snap2 = octobot_flow_entities.ExchangeAccountElements(
            orders=exchange_data_import.OrdersDetails(open_orders=[{"id": "last-wins"}]),
            trades=[_trade_stub("t-second")],
            positions=[exchange_data_import.PositionDetails()],
        )
        automation = octobot_flow_entities.AutomationDetails(
            metadata=octobot_flow_entities.AutomationMetadata(automation_id="aid"),
            exchange_account_elements=octobot_flow_entities.ExchangeAccountElements(),
        )
        target = automation.exchange_account_elements
        assert target is not None
        target.trades.append(_trade_stub("t-existing"))
        changed = target.merge_synchronized_snapshots([snap1, snap2])
        assert octobot_flow_enums_import.ChangedElements.TRADES in changed
        tid = octobot_trading_enums_import.ExchangeConstantsOrderColumns.EXCHANGE_TRADE_ID.value
        trade_ids = [trade[tid] for trade in target.trades]
        assert trade_ids == ["t-existing", "t-first", "t-second"]
        assert target.orders.open_orders == [{"id": "last-wins"}]


class TestMergeSynchronizedSnapshotsPreservesTransactions:
    def test_merges_transactions_only_once_per_txid(self):
        snap1 = octobot_flow_entities.ExchangeAccountElements(
            transactions=[_tx_stub("tx-a")],
        )
        snap2 = octobot_flow_entities.ExchangeAccountElements(
            transactions=[_tx_stub("tx-a"), _tx_stub("tx-b")],
        )
        automation = octobot_flow_entities.AutomationDetails(
            metadata=octobot_flow_entities.AutomationMetadata(automation_id="aid"),
            exchange_account_elements=octobot_flow_entities.ExchangeAccountElements(),
        )
        tx_key = octobot_trading_enums_import.ExchangeConstantsTransactionColumns.TXID.value
        automation.exchange_account_elements.transactions.append(_tx_stub("tx-existing"))
        automation.exchange_account_elements.merge_synchronized_snapshots([snap1, snap2])
        txs = automation.exchange_account_elements.transactions
        assert [t[tx_key] for t in txs] == ["tx-existing", "tx-a", "tx-b"]


class TestClearPostIterationAfterMerge:
    def test_clears_updated_exchange_account_elements_from_recall_wrapper(self):
        post_iteration_name = octobot_flow_entities.PostIterationActionsDetails.__name__
        action_result = {
            octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__: {
                "last_execution_result": {
                    post_iteration_name: {
                        "updated_exchange_account_elements": {"trades": []},
                        "stop_automation": False,
                    },
                    "pid": 42,
                },
            }
        }
        octobot_flow_entities.PostIterationActionsDetails.post_iteration_clear_from_action_result(
            action_result
        )
        inner_post_iteration = action_result[
            octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__
        ]["last_execution_result"][post_iteration_name]
        assert "updated_exchange_account_elements" not in inner_post_iteration
        assert inner_post_iteration["stop_automation"] is False

    def test_clear_after_sync_clears_post_iteration_on_action_result(self):
        post_iteration_name = octobot_flow_entities.PostIterationActionsDetails.__name__
        action = octobot_flow_entities.DSLScriptActionDetails(
            id="process-action",
            dsl_script="run_octobot_process('folder')",
        )
        action.result = {
            octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__: {
                "last_execution_result": {
                    post_iteration_name: {
                        "updated_exchange_account_elements": {
                            "trades": [_trade_stub("merged-trade")],
                        },
                    },
                },
            }
        }
        automation = octobot_flow_entities.AutomationDetails(
            metadata=octobot_flow_entities.AutomationMetadata(automation_id="aid"),
            exchange_account_elements=octobot_flow_entities.ExchangeAccountElements(),
        )
        snapshot = octobot_flow_entities.ExchangeAccountElements(
            trades=[_trade_stub("merged-trade")],
        )
        executor_action = actions_executor_import.ActionsExecutor(
            None,
            None,
            commons_profiles.ProfileData(),
            automation,
            [action],
            False,
        )
        executor_action._sync_after_execution([snapshot])
        executor_action._clear_post_iteration_after_merge_from_action_results()
        inner_post_iteration = action.result[
            octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__
        ]["last_execution_result"][post_iteration_name]
        assert "updated_exchange_account_elements" not in inner_post_iteration
        trade_id_key = octobot_trading_enums_import.ExchangeConstantsOrderColumns.EXCHANGE_TRADE_ID.value
        assert automation.exchange_account_elements.trades[0][trade_id_key] == "merged-trade"

    def test_clear_without_post_iteration_eae_preserves_recall_fields(self):
        action = octobot_flow_entities.DSLScriptActionDetails(
            id="process-action",
            dsl_script="run_octobot_process('folder')",
        )
        action.result = {
            octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__: {
                "last_execution_result": {
                    "pid": 42,
                    "init_state_ok": True,
                },
            }
        }
        automation = octobot_flow_entities.AutomationDetails(
            metadata=octobot_flow_entities.AutomationMetadata(automation_id="aid"),
        )
        executor_action = actions_executor_import.ActionsExecutor(
            None,
            None,
            commons_profiles.ProfileData(),
            automation,
            [action],
            False,
        )
        executor_action._clear_post_iteration_after_merge_from_action_results()
        inner_last = action.result[
            octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__
        ]["last_execution_result"]
        assert inner_last["pid"] == 42
        assert inner_last["init_state_ok"] is True


class TestMergeThenTrimIntegration:
    def test_large_snapshot_merge_then_trim_obey_live_window(self):
        order_columns = octobot_trading_enums_import.ExchangeConstantsOrderColumns
        trades = [
            {
                order_columns.EXCHANGE_TRADE_ID.value: f"trade-{trade_index}",
                order_columns.SYMBOL.value: "BTC/USDT",
                order_columns.TIMESTAMP.value: float(trade_index),
            }
            for trade_index in range(120)
        ]
        snapshot = octobot_flow_entities.ExchangeAccountElements(trades=trades)
        automation = octobot_flow_entities.AutomationDetails(
            metadata=octobot_flow_entities.AutomationMetadata(automation_id="aid"),
            exchange_account_elements=octobot_flow_entities.ExchangeAccountElements(),
        )
        executor_action = actions_executor_import.ActionsExecutor(
            None,
            None,
            commons_profiles.ProfileData(),
            automation,
            [],
            False,
        )
        executor_action._sync_after_execution([snapshot])
        automation.exchange_account_elements.trim_trades_to_live_window(100)
        assert len(automation.exchange_account_elements.trades) == 100
        assert len(automation.exchange_account_elements.trade_summaries.get("BTC/USDT", [])) == 20
