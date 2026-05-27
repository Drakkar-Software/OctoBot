import asyncio
import datetime
import pathlib
import tempfile

import mock
import pytest

import octobot_sync.chain.evm as sync_evm_module
import octobot_sync.sync
import octobot.community.authentication as community_authentication_module
import octobot.community.local_authenticator as local_authenticator_module
import octobot_commons.user_root_folder_provider as user_root_folder_provider_module
import octobot_node.constants as octobot_node_constants
import octobot_node.errors as node_errors_module
import octobot_node.scheduler
import octobot_node.scheduler.api as scheduler_api
import octobot_node.scheduler.tasks as scheduler_tasks
import octobot_protocol.models as protocol_models

import tests.scheduler as scheduler_tests

_TEST_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_TEST_WALLET_PASSPHRASE = "strategiesCRUD1!"
_DOOMED_STRATEGY_ID = "functional-strategy-doomed"
_FUNCTIONAL_STRATEGY_ID = "functional-strategy-id"
_WORKFLOW_RESULT_TIMEOUT_SECONDS = 120.0


@pytest.fixture
def patched_user_action_workflow_max_iteration_retries():
    with mock.patch.object(octobot_node_constants, "USER_ACTION_WORKFLOW_MAX_ITERATION_RETRIES", 2):
        yield


@pytest.fixture
def temp_dbos_scheduler_strategy_crud(
    patched_user_action_workflow_max_iteration_retries,  # noqa: ARG001
):
    """Mirrors ``tests.scheduler.temp_dbos_scheduler``; requests the patch fixture so registration sees capped retries."""
    with tempfile.NamedTemporaryFile() as temp_file:
        dbos_runtime = scheduler_tests.init_scheduler(temp_file.name)
        dbos_runtime.reset_system_database()
        dbos_runtime.launch()
        try:
            yield octobot_node.scheduler.SCHEDULER
        finally:
            dbos_runtime.destroy()


async def _run_user_action_to_completion(
    wallet_address: str,
    user_action: protocol_models.UserAction,
    *,
    expect_exceptions: tuple[type[BaseException], ...] = (),
) -> str:
    workflow_id = await scheduler_tasks.trigger_user_action_workflow(user_action, wallet_address)
    workflow_handle = await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(workflow_id)
    try:
        await asyncio.wait_for(workflow_handle.get_result(), timeout=_WORKFLOW_RESULT_TIMEOUT_SECONDS)
    except BaseException as caught:
        if expect_exceptions and isinstance(caught, expect_exceptions):
            return workflow_id
        raise
    return workflow_id


def _assert_listed_user_actions_match_expected_id_status_pairs(
    listed_user_actions: list[protocol_models.UserAction],
    expected_id_status_pairs: list[tuple[str, protocol_models.UserActionStatus]],
) -> None:
    actual_sorted = sorted((row.id, row.status) for row in listed_user_actions)
    expected_sorted = sorted(expected_id_status_pairs)
    assert actual_sorted == expected_sorted


@pytest.mark.asyncio
class TestExecuteUserActionStrategyCrud:
    async def test_create_edit_delete_strategies(
        self,
        tmp_path: pathlib.Path,
        temp_dbos_scheduler_strategy_crud,
    ):
        # Step: Isolate sync collections under a temp user-root folder (restored in ``finally``).
        user_root_provider = user_root_folder_provider_module.instance()
        previous_user_root = user_root_provider.get_root()
        test_user_root = tmp_path / "functional_strategies_user_root"
        user_root_provider.set_root(str(test_user_root))

        authentication_instance: community_authentication_module.CommunityAuthentication | None = None
        sample_timestamp = datetime.datetime(2026, 5, 1, 12, 0, 0, tzinfo=datetime.UTC)

        # Step: Nested builders for protocol payloads; user actions start as PENDING so active-queue listings match enqueue snapshots.
        def wrap_configuration(payload) -> protocol_models.UserActionConfiguration:
            return protocol_models.UserActionConfiguration.from_json(payload.to_json())

        def build_strategy(
            *,
            strategy_id: str,
            name: str = "Functional strategy",
            version: str = "1.0.0",
        ) -> protocol_models.Strategy:
            configuration = protocol_models.GenericProcessConfiguration(
                configuration_type=protocol_models.ActionConfigurationType.GENERIC_PROCESS,
                profile_data={},
            )
            return protocol_models.Strategy(
                id=strategy_id,
                version=version,
                name=name,
                reference_market="USDT",
                created_at=sample_timestamp,
                updated_at=sample_timestamp,
                configuration=protocol_models.StrategyConfiguration(configuration),
            )

        def build_create_strategy_user_action(
            *,
            user_action_id: str,
            strategy: protocol_models.Strategy,
        ) -> protocol_models.UserAction:
            payload = protocol_models.CreateStrategyConfiguration(
                action_type=protocol_models.UserActionType.STRATEGY_CREATE,
                configuration=strategy,
            )
            return protocol_models.UserAction(
                id=user_action_id,
                status=protocol_models.UserActionStatus.PENDING,
                created_at=sample_timestamp,
                updated_at=sample_timestamp,
                configuration=wrap_configuration(payload),
            )

        def build_edit_strategy_user_action(
            *,
            user_action_id: str,
            strategy_id: str,
            strategy: protocol_models.Strategy,
        ) -> protocol_models.UserAction:
            payload = protocol_models.EditStrategyConfiguration(
                action_type=protocol_models.UserActionType.STRATEGY_EDIT,
                id=strategy_id,
                configuration=strategy,
            )
            return protocol_models.UserAction(
                id=user_action_id,
                status=protocol_models.UserActionStatus.PENDING,
                created_at=sample_timestamp,
                updated_at=sample_timestamp,
                configuration=wrap_configuration(payload),
            )

        def build_delete_strategy_user_action(
            *,
            user_action_id: str,
            strategy_id: str,
        ) -> protocol_models.UserAction:
            payload = protocol_models.DeleteStrategyConfiguration(
                action_type=protocol_models.UserActionType.STRATEGY_DELETE,
                id=strategy_id,
            )
            return protocol_models.UserAction(
                id=user_action_id,
                status=protocol_models.UserActionStatus.PENDING,
                created_at=sample_timestamp,
                updated_at=sample_timestamp,
                configuration=wrap_configuration(payload),
            )

        try:
            # Step: Import dev wallet; ``wallet_address`` ties StrategyProvider paths and ``list_user_actions`` filtering together.
            authentication_configuration = local_authenticator_module.get_stateless_configuration()
            authentication_instance = community_authentication_module.CommunityAuthentication(
                config=authentication_configuration,
                use_as_singleton=False,
            )
            authentication_instance.import_wallet(
                _TEST_PRIVATE_KEY,
                _TEST_WALLET_PASSPHRASE,
                None,
                True,
            )
            wallet_address = sync_evm_module.address_from_evm_key(_TEST_PRIVATE_KEY).lower()

            # Step: Filesystem-backed provider for this test root (also patched as ``StrategyProvider.instance()``).
            strategy_provider = octobot_sync.sync.StrategyProvider(base_folder=str(test_user_root))
            real_create_item = strategy_provider.create_item

            # Step: Steer ``create_item`` so the doomed strategy id fails before persistence (happy path uses real method).
            def create_item_fail_doomed_create(
                address: str,
                strategy: protocol_models.Strategy,
            ) -> protocol_models.Strategy:
                if strategy.id == _DOOMED_STRATEGY_ID:
                    raise node_errors_module.InvalidUserActionPayloadError("forced doomed create failure")
                return real_create_item(address, strategy)

            with (
                mock.patch.object(
                    community_authentication_module.CommunityAuthentication,
                    "instance",
                    return_value=authentication_instance,
                ),
                mock.patch.object(
                    octobot_sync.sync.StrategyProvider,
                    "instance",
                    return_value=strategy_provider,
                ),
            ):
                create_item_mock = mock.Mock(side_effect=create_item_fail_doomed_create)
                with mock.patch.object(
                    strategy_provider,
                    "create_item",
                    create_item_mock,
                ):
                    assert strategy_provider.list_items(wallet_address) == []

                    # Step 1 — Create (doomed): ``InvalidUserActionPayloadError`` from patched create; workflow fails; nothing persisted.
                    doomed_create = build_create_strategy_user_action(
                        user_action_id="ua-strategy-create-fail",
                        strategy=build_strategy(strategy_id=_DOOMED_STRATEGY_ID),
                    )
                    await _run_user_action_to_completion(
                        wallet_address,
                        doomed_create,
                    )

                    # Step 1 (continued) — Listing: only the doomed row, FAILED with executor-built ``StrategyActionResult``.
                    listed_after_doomed = await scheduler_api.list_user_actions(wallet_address, active_only=True)
                    _assert_listed_user_actions_match_expected_id_status_pairs(
                        listed_after_doomed,
                        [(doomed_create.id, protocol_models.UserActionStatus.FAILED)],
                    )
                    doomed_latest = next(row for row in listed_after_doomed if row.id == doomed_create.id)
                    assert doomed_latest.result is not None
                    doomed_inner = doomed_latest.result.actual_instance
                    assert isinstance(doomed_inner, protocol_models.StrategyActionResult)
                    assert doomed_inner.result_type == protocol_models.UserActionResultType.STRATEGY
                    assert doomed_inner.error_message == protocol_models.StrategyActionResultErrorMessage.INVALID_CONFIGURATION
                    assert doomed_inner.error_details is not None
                    assert "forced doomed create failure" in doomed_inner.error_details

                    # Step 2 — Create (happy path): workflow completes; provider stores strategy.
                    happy_create = build_create_strategy_user_action(
                        user_action_id="ua-strategy-create",
                        strategy=build_strategy(strategy_id=_FUNCTIONAL_STRATEGY_ID),
                    )
                    await _run_user_action_to_completion(wallet_address, happy_create)

                    # Step 2 (continued) — Listing: doomed FAILED + happy COMPLETED; verify persisted strategy.
                    listed_after_create = await scheduler_api.list_user_actions(wallet_address, active_only=True)
                    _assert_listed_user_actions_match_expected_id_status_pairs(
                        listed_after_create,
                        [
                            (doomed_create.id, protocol_models.UserActionStatus.FAILED),
                            (happy_create.id, protocol_models.UserActionStatus.COMPLETED),
                        ],
                    )
                    created_latest = next(row for row in listed_after_create if row.id == happy_create.id)
                    assert created_latest.result is not None
                    created_inner = created_latest.result.actual_instance
                    assert isinstance(created_inner, protocol_models.StrategyActionResult)
                    assert created_inner.error_message is None

                    persisted_created_strategy = strategy_provider.get_item(
                        wallet_address,
                        _FUNCTIONAL_STRATEGY_ID,
                    )
                    assert persisted_created_strategy.name == "Functional strategy"
                    assert len(strategy_provider.list_items(wallet_address)) == 1

                    # Step 3 — Edit: rename strategy while keeping the same id.
                    edited_strategy = build_strategy(
                        strategy_id=_FUNCTIONAL_STRATEGY_ID,
                        name="Functional strategy renamed",
                    )
                    edit_strategy_action = build_edit_strategy_user_action(
                        user_action_id="ua-strategy-edit",
                        strategy_id=_FUNCTIONAL_STRATEGY_ID,
                        strategy=edited_strategy,
                    )
                    await _run_user_action_to_completion(wallet_address, edit_strategy_action)

                    # Step 3 (continued) — Listing adds COMPLETED edit row; strategy updated in provider.
                    listed_after_edit = await scheduler_api.list_user_actions(wallet_address, active_only=True)
                    _assert_listed_user_actions_match_expected_id_status_pairs(
                        listed_after_edit,
                        [
                            (doomed_create.id, protocol_models.UserActionStatus.FAILED),
                            (happy_create.id, protocol_models.UserActionStatus.COMPLETED),
                            (edit_strategy_action.id, protocol_models.UserActionStatus.COMPLETED),
                        ],
                    )
                    persisted_edited_strategy = strategy_provider.get_item(
                        wallet_address,
                        _FUNCTIONAL_STRATEGY_ID,
                    )
                    assert persisted_edited_strategy.name == "Functional strategy renamed"

                    # Step 4 — Delete: remove strategy from provider; listing gains COMPLETED delete row.
                    delete_strategy_action = build_delete_strategy_user_action(
                        user_action_id="ua-strategy-delete",
                        strategy_id=_FUNCTIONAL_STRATEGY_ID,
                    )
                    await _run_user_action_to_completion(wallet_address, delete_strategy_action)

                    # Step 4 (continued) — Full listing is four terminal rows; strategies collection empty.
                    listed_after_delete = await scheduler_api.list_user_actions(wallet_address, active_only=True)
                    _assert_listed_user_actions_match_expected_id_status_pairs(
                        listed_after_delete,
                        [
                            (doomed_create.id, protocol_models.UserActionStatus.FAILED),
                            (happy_create.id, protocol_models.UserActionStatus.COMPLETED),
                            (edit_strategy_action.id, protocol_models.UserActionStatus.COMPLETED),
                            (delete_strategy_action.id, protocol_models.UserActionStatus.COMPLETED),
                        ],
                    )
                    delete_latest = next(row for row in listed_after_delete if row.id == delete_strategy_action.id)
                    assert delete_latest.result is not None
                    delete_inner = delete_latest.result.actual_instance
                    assert isinstance(delete_inner, protocol_models.StrategyActionResult)
                    assert delete_inner.error_message is None

                    # Step: Collection layer confirms strategy delete (no item, empty list).
                    with pytest.raises(octobot_sync.sync.ItemNotFoundError):
                        strategy_provider.get_item(wallet_address, _FUNCTIONAL_STRATEGY_ID)
                    assert strategy_provider.list_items(wallet_address) == []
        finally:
            # Step: Tear down wallet task and restore prior user-root path.
            if authentication_instance is not None:
                await authentication_instance.stop()
            user_root_provider.set_root(previous_user_root)
