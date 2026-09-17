#  Demo-only agent seed wallet secrets (insecure by design, committed for local/Cloud QA).
#  Never fund this wallet on mainnet or use for real trading.

import octobot_sync.auth.provider as sync_auth_provider_module

import octobot_node.agent_seed.constants as demo_agent_seed_constants

# Hardcoded dev-only demo wallet — insecure by design.
DEMO_INSECURE_WALLET_PRIVATE_KEY = (
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
)

# Hardcoded dev-only demo wallet passphrase — insecure by design (Node requires len >= 8).
DEMO_INSECURE_WALLET_PASSPHRASE = "demodemo"


def assert_demo_insecure_wallet_matches_node_constants() -> None:
    derived_user_id = sync_auth_provider_module.derive_user_id(
        DEMO_INSECURE_WALLET_PRIVATE_KEY,
    )
    if derived_user_id != demo_agent_seed_constants.DEMO_AGENT_SEED_USER_ID:
        raise ValueError(
            "DEMO_INSECURE_WALLET_PRIVATE_KEY does not derive to DEMO_AGENT_SEED_USER_ID; "
            "update octobot_node.agent_seed.constants"
        )
