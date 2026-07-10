#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import mock
import pytest
import uuid

from octobot_node.scheduler.generic_process_octobot import create_generic_process_bot

from tests.scheduler import temp_dbos_scheduler


class TestCreateGenericProcessBotCreatesMissingStrategy:
    @pytest.mark.asyncio
    async def test_create_generic_process_bot_creates_missing_strategy(
        self,
        tmp_path,
        temp_dbos_scheduler,
    ) -> None:
        import octobot_commons.constants as commons_constants_module
        import octobot_commons.user_root_folder_provider as user_root_folder_provider_module
        import octobot_node.constants as octobot_node_constants_module
        import octobot_protocol.models as protocol_models_module
        import octobot_sync.sync.collection_providers as collection_providers_module
        import octobot.community.authentication as community_authentication_module
        from tests.functional_tests.util import authenticator_mocks as authenticator_mocks_module
        from tests.functional_tests.util import workflow_common as workflow_common_module

        user_root_provider = user_root_folder_provider_module.instance()
        previous_user_root = user_root_provider.get_root()
        test_user_root = tmp_path / "create_generic_process_bot_user_root"
        user_root_provider.set_root(str(test_user_root))
        user_id = workflow_common_module.SIMULATOR_GRID_TEST_COMMUNITY_USER_ID
        authentication_instance = authenticator_mocks_module.build_community_authentication(
            workflow_common_module.SIMULATOR_GRID_TEST_PRIVATE_KEY,
            workflow_common_module.SIMULATOR_GRID_TEST_WALLET_PASSPHRASE,
        )

        try:
            with mock.patch.object(
                community_authentication_module.CommunityAuthentication,
                "instance",
                return_value=authentication_instance,
            ):
                automation_id = await create_generic_process_bot(user_id, "My manual OctoBot")

            stored_strategy = collection_providers_module.StrategyProvider.instance().get_item(
                user_id,
                octobot_node_constants_module.NON_TRADING_GENERIC_PROCESS_OCTOBOT_STRATEGY_ID,
            )
            assert stored_strategy.reference_market == commons_constants_module.DEFAULT_REFERENCE_MARKET
            generic_process_configuration = stored_strategy.configuration.actual_instance
            assert isinstance(generic_process_configuration, protocol_models_module.GenericProcessConfiguration)
            assert generic_process_configuration.profile_data is None
            assert automation_id
            assert len(automation_id) == octobot_node_constants_module.PARENT_WORKFLOW_ID_LENGTH
        finally:
            user_root_provider.set_root(previous_user_root)


class TestCreateGenericProcessBotReusesExistingStrategy:
    @pytest.mark.asyncio
    async def test_create_generic_process_bot_reuses_existing_strategy(
        self,
        tmp_path,
        temp_dbos_scheduler,
    ) -> None:
        import octobot_commons.user_root_folder_provider as user_root_folder_provider_module
        import octobot_node.constants as octobot_node_constants_module
        import octobot_sync.sync.collection_providers as collection_providers_module
        import octobot.community.authentication as community_authentication_module
        from tests.functional_tests.util import authenticator_mocks as authenticator_mocks_module
        from tests.functional_tests.util import workflow_common as workflow_common_module

        user_root_provider = user_root_folder_provider_module.instance()
        previous_user_root = user_root_provider.get_root()
        test_user_root = tmp_path / "create_generic_process_bot_existing_strategy_user_root"
        user_root_provider.set_root(str(test_user_root))
        user_id = workflow_common_module.SIMULATOR_GRID_TEST_COMMUNITY_USER_ID
        authentication_instance = authenticator_mocks_module.build_community_authentication(
            workflow_common_module.SIMULATOR_GRID_TEST_PRIVATE_KEY,
            workflow_common_module.SIMULATOR_GRID_TEST_WALLET_PASSPHRASE,
        )

        try:
            with mock.patch.object(
                community_authentication_module.CommunityAuthentication,
                "instance",
                return_value=authentication_instance,
            ):
                first_automation_id = await create_generic_process_bot(user_id, "First manual OctoBot")
                strategy_after_first_create = collection_providers_module.StrategyProvider.instance().get_item(
                    user_id,
                    octobot_node_constants_module.NON_TRADING_GENERIC_PROCESS_OCTOBOT_STRATEGY_ID,
                )
                second_automation_id = await create_generic_process_bot(user_id, "Second manual OctoBot")
                strategy_after_second_create = collection_providers_module.StrategyProvider.instance().get_item(
                    user_id,
                    octobot_node_constants_module.NON_TRADING_GENERIC_PROCESS_OCTOBOT_STRATEGY_ID,
                )

            assert first_automation_id != second_automation_id
            assert strategy_after_second_create.id == strategy_after_first_create.id
            assert strategy_after_second_create.version == strategy_after_first_create.version
        finally:
            user_root_provider.set_root(previous_user_root)


class TestCreateGenericProcessBotUsesProvidedAutomationId:
    @pytest.mark.asyncio
    async def test_create_generic_process_bot_uses_provided_automation_id(
        self,
        tmp_path,
        temp_dbos_scheduler,
    ) -> None:
        import octobot_commons.user_root_folder_provider as user_root_folder_provider_module
        import octobot.community.authentication as community_authentication_module
        from tests.functional_tests.util import authenticator_mocks as authenticator_mocks_module
        from tests.functional_tests.util import workflow_common as workflow_common_module

        user_root_provider = user_root_folder_provider_module.instance()
        previous_user_root = user_root_provider.get_root()
        test_user_root = tmp_path / "create_generic_process_bot_provided_automation_id_user_root"
        user_root_provider.set_root(str(test_user_root))
        user_id = workflow_common_module.SIMULATOR_GRID_TEST_COMMUNITY_USER_ID
        provided_automation_id = str(uuid.uuid4())
        authentication_instance = authenticator_mocks_module.build_community_authentication(
            workflow_common_module.SIMULATOR_GRID_TEST_PRIVATE_KEY,
            workflow_common_module.SIMULATOR_GRID_TEST_WALLET_PASSPHRASE,
        )

        try:
            with mock.patch.object(
                community_authentication_module.CommunityAuthentication,
                "instance",
                return_value=authentication_instance,
            ):
                automation_id = await create_generic_process_bot(
                    user_id,
                    "Provided id OctoBot",
                    automation_id=provided_automation_id,
                )

            assert automation_id == provided_automation_id
        finally:
            user_root_provider.set_root(previous_user_root)
