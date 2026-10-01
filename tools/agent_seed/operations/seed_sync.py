#  Demo-only agent seed sync collection writes and wallet import.

import datetime
import pathlib

import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers

import octobot.constants as octobot_constants
import octobot.community.authentication as community_authentication
import octobot_commons.configuration as octobot_commons_configuration
import octobot_commons.configuration.config_file_manager as config_file_manager
import octobot_commons.user_root_folder_provider as user_root_folder_provider

import octobot_node.agent_seed.constants as demo_agent_seed_constants

import tools.agent_seed.protocol.builders as agent_seed_protocol_builders
import tools.agent_seed.secrets as agent_seed_secrets


def _create_or_update_exchange_config(
    account_provider: collection_providers.AccountProvider,
    user_id: str,
    exchange_config: protocol_models.ExchangeConfig,
) -> None:
    try:
        account_provider.create_exchange_config(user_id, exchange_config)
    except collection_errors.DuplicateItemError:
        account_provider.update_exchange_config(user_id, exchange_config)


def _create_or_update_account(
    account_provider: collection_providers.AccountProvider,
    user_id: str,
    account: protocol_models.Account,
) -> None:
    try:
        account_provider.create_account(user_id, account)
    except collection_errors.DuplicateItemError:
        account_provider.update_account(user_id, account)


def _create_or_update_strategy(
    strategy_provider: collection_providers.StrategyProvider,
    user_id: str,
    strategy: protocol_models.Strategy,
) -> None:
    try:
        strategy_provider.create_item(user_id, strategy)
    except collection_errors.DuplicateItemError:
        strategy_provider.update_item(user_id, strategy)


def _seed_account_trading_state(
    trading_provider: collection_providers.AccountTradingProvider,
    user_id: str,
    account_id: str,
) -> None:
    trading_provider.save_state(
        user_id,
        account_id,
        protocol_models.AccountTradingState(
            version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=protocol_models.AccountTrading(
                updated_at=datetime.datetime.now(datetime.UTC),
            ),
        ),
    )


def write_sync_collections(user_folder: pathlib.Path, user_id: str) -> None:
    account_provider = collection_providers.AccountProvider(base_folder=str(user_folder))
    strategy_provider = collection_providers.StrategyProvider(base_folder=str(user_folder))
    trading_provider = collection_providers.AccountTradingProvider(
        base_folder=str(user_folder),
    )

    _create_or_update_exchange_config(
        account_provider,
        user_id,
        agent_seed_protocol_builders.build_kraken_sim_exchange_config(),
    )
    grid_account = agent_seed_protocol_builders.build_sim_exchange_account(
        account_id=demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_GRID_ID,
        account_name=demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_GRID_DISPLAY_NAME,
        usdc_total=demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_GRID_USDC,
    )
    index_account = agent_seed_protocol_builders.build_sim_exchange_account(
        account_id=demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_INDEX_IDLE_ID,
        account_name=demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_INDEX_IDLE_DISPLAY_NAME,
        usdc_total=demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_INDEX_IDLE_USDC,
    )
    _create_or_update_account(account_provider, user_id, grid_account)
    _create_or_update_account(account_provider, user_id, index_account)
    _create_or_update_strategy(
        strategy_provider,
        user_id,
        agent_seed_protocol_builders.build_grid_strategy(),
    )
    _create_or_update_strategy(
        strategy_provider,
        user_id,
        agent_seed_protocol_builders.build_index_strategy(),
    )
    _seed_account_trading_state(
        trading_provider,
        user_id,
        demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_GRID_ID,
    )
    _seed_account_trading_state(
        trading_provider,
        user_id,
        demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_INDEX_IDLE_ID,
    )


def _load_writable_user_configuration() -> octobot_commons_configuration.Configuration:
    configuration = octobot_commons_configuration.Configuration(
        config_file_manager.get_user_config(),
        user_root_folder_provider.get_user_profiles_folder(),
        octobot_constants.CONFIG_FILE_SCHEMA,
        octobot_constants.PROFILE_FILE_SCHEMA,
    )
    configuration.read(should_raise=False)
    if configuration.config is None:
        configuration.config = {}
    return configuration


def _is_demo_wallet_present(
    community_auth: community_authentication.CommunityAuthentication,
) -> bool:
    demo_address = demo_agent_seed_constants.DEMO_AGENT_SEED_WALLET_EVM_ADDRESS.lower()
    return any(
        wallet.address.lower() == demo_address
        for wallet in community_auth.list_wallets()
    )


def import_demo_wallet() -> None:
    authentication_configuration = _load_writable_user_configuration()
    community_auth = community_authentication.CommunityAuthentication(
        config=authentication_configuration,
        use_as_singleton=True,
    )
    if _is_demo_wallet_present(community_auth):
        return
    community_auth.import_wallet(
        agent_seed_secrets.DEMO_INSECURE_WALLET_PRIVATE_KEY,
        agent_seed_secrets.DEMO_INSECURE_WALLET_PASSPHRASE,
        demo_agent_seed_constants.DEMO_AGENT_SEED_WALLET_DISPLAY_NAME,
        is_admin=True,
    )
