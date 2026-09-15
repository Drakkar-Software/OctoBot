#  Drakkar-Software OctoBot-Sync
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.

import typing

import octobot_sync.sync.collection_backend.tolerant_state_loading as tolerant_state_loading_module
import octobot_sync.sync.collection_providers.user_strategy_provider as strategy_provider_module


def strategy_tolerant_loading_kwargs() -> dict[str, typing.Any]:
    return {
        "model_sanitizers": strategy_provider_module.StrategyProvider.MODEL_SANITIZERS,
        "model_fallbacks": strategy_provider_module.StrategyProvider.MODEL_FALLBACKS,
    }


def make_loader(
    collection: str,
    state_class: typing.Any = None,
    **loader_kwargs: typing.Any,
) -> tolerant_state_loading_module.TolerantStateLoader:
    return tolerant_state_loading_module.TolerantStateLoader(
        state_class,
        collection=collection,
        **loader_kwargs,
    )
