#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  Demo-only agent seed fixture identifiers. Not for production wallets or real funds.
#  Private key material lives only in tools/agent_seed/secrets.py (insecure by design).

DEMO_AGENT_SEED_WALLET_DISPLAY_NAME = "demo"

# Anvil / Hardhat account #1 (public test vector; matches tools.agent_seed.secrets).
DEMO_AGENT_SEED_WALLET_EVM_ADDRESS = "0x70997970c51812dc3a010c7d01b50e0d17dc79c8"

# Starfish user_id for the demo agent-seed wallet (derived from demo insecure key at fixture design time).
DEMO_AGENT_SEED_USER_ID = "49f2d71b4bba99febdca5c0da6e4b60b"

DEMO_AGENT_SEED_STRATEGY_VERSION = "1.0.0"
DEMO_AGENT_SEED_MARKER_VERSION = "1"

DEMO_AGENT_SEED_EXCHANGE_CONFIG_ID = "agent-seed-kraken-sim-exchange-config"
DEMO_AGENT_SEED_ACCOUNT_GRID_ID = "agent-seed-kraken-sim-account-grid"
DEMO_AGENT_SEED_ACCOUNT_INDEX_IDLE_ID = "agent-seed-kraken-sim-account-index-idle"
DEMO_AGENT_SEED_STRATEGY_GRID_ID = "agent-seed-strategy-grid-btc-usdc"
DEMO_AGENT_SEED_STRATEGY_INDEX_ID = "agent-seed-strategy-index-btc-eth-sol"
# Stable agent-seed grid automation parent id (Node create-automation requires canonical lowercase UUID).
DEMO_AGENT_SEED_AUTOMATION_GRID_ID = "a0000000-0000-4000-8000-000000000001"

DEMO_AGENT_SEED_GRID_SYMBOL = "BTC/USDC"
DEMO_AGENT_SEED_GRID_SPREAD = 2000.0
DEMO_AGENT_SEED_GRID_INCREMENT = 500.0
DEMO_AGENT_SEED_GRID_BUY_COUNT = 3
DEMO_AGENT_SEED_GRID_SELL_COUNT = 3

DEMO_AGENT_SEED_INDEX_REBALANCE_TRIGGER_MIN_PERCENT = 10.0

DEMO_AGENT_SEED_ACCOUNT_GRID_USDC = 1000.0
DEMO_AGENT_SEED_ACCOUNT_INDEX_IDLE_USDC = 500.0
DEMO_AGENT_SEED_ACCOUNT_GRID_DISPLAY_NAME = "Seed kraken A"
DEMO_AGENT_SEED_ACCOUNT_INDEX_IDLE_DISPLAY_NAME = "Seed kraken B"

DEMO_AGENT_SEED_EXCHANGE_INTERNAL_NAME = "kraken"

DEMO_AGENT_SEED_GRID_AUTOMATION_DISPLAY_NAME = "Agent seed BTC/USDC grid"

DEMO_AGENT_SEED_FORBIDDEN_ACTION_DETAIL = (
    "Demo agent-seed wallet cannot create live exchange accounts or automations"
)

DEMO_AGENT_SEED_CLEAR_LOCKED_SQLITE_MESSAGE_PREFIX = (
    "Agent seed clear failed: stop the OctoBot node first — tasks.db is locked"
)
