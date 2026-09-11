#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import dataclasses
import typing

import octobot_commons.configuration as configuration

import octobot.configuration_manager as configuration_manager
import octobot.enums as octobot_enums
import octobot_protocol.models as protocol_models
import octobot_sync.sync.collection_providers as collection_providers

import octobot.community.authentication as community_authentication
import octobot.community.errors_upload.sentry_tracker as sentry_tracker
import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.recording as journal_recording
import octobot.community.node_journal.state as journal_state


@dataclasses.dataclass(frozen=True)
class ExistingConfigSnapshot:
    wallet_configured: bool
    account_count: int
    reconciled: bool


_reconcile_completed = False


def build_existing_config_snapshot() -> ExistingConfigSnapshot:
    auth = community_authentication.CommunityAuthentication.instance()
    wallet_configured = auth is not None and auth.is_node_wallet_configured()
    account_count = 0
    if wallet_configured:
        wallet_user_ids = collection_providers.AccountProvider.instance().list_collectable_wallet_ids()
        for wallet_id in wallet_user_ids:
            account_count += len(collection_providers.AccountProvider.instance().list_accounts(wallet_id))
    has_existing_config = wallet_configured or account_count > 0
    return ExistingConfigSnapshot(
        wallet_configured=wallet_configured,
        account_count=account_count,
        reconciled=has_existing_config,
    )


def initialize_journal(config: configuration.Configuration) -> None:
    sentry_tracker.init_sentry_tracker(metrics_enabled=False)
    if not journal_module.is_journal_enabled():
        return
    distribution = configuration_manager.get_distribution(config.config)
    if distribution is not octobot_enums.OctoBotDistribution.NODE:
        return
    journal_module.initialize_for_config(config)
    snapshot = build_existing_config_snapshot()
    if snapshot.reconciled:
        journal_recording.record_existing_config_detected(
            wallet_configured=snapshot.wallet_configured,
            account_count=snapshot.account_count,
        )


def record_node_startup_succeeded(config: configuration.Configuration) -> None:
    journal_module.initialize_for_config(config)
    snapshot = build_existing_config_snapshot()
    journal_recording.record_process_startup_succeeded(
        wallet_configured=snapshot.wallet_configured,
        new_install=not snapshot.reconciled,
        reconciled=snapshot.reconciled,
    )


def record_node_startup_failed(
    error: BaseException,
    *,
    startup_phase: journal_enums.JournalStartupPhase,
    force_exit: bool,
    config: typing.Optional[configuration.Configuration] = None,
) -> None:
    resolved_config = config if config is not None else journal_state.get_config()
    if resolved_config is not None:
        journal_module.initialize_for_config(resolved_config)
    snapshot = build_existing_config_snapshot()
    journal_recording.record_process_startup_failed(
        startup_phase=startup_phase,
        error=error,
        force_exit=force_exit,
        wallet_configured=snapshot.wallet_configured,
        new_install=not snapshot.reconciled,
        reconciled=snapshot.reconciled,
    )


def _distinct_automation_ids_from_states(
    automation_states: list[protocol_models.AutomationState],
) -> list[str]:
    return sorted({
        automation_state.id
        for automation_state in automation_states
        if automation_state.id
    })


async def complete_reconcile_automations(
    config: typing.Optional[configuration.Configuration] = None,
) -> None:
    global _reconcile_completed
    if not journal_module.is_journal_enabled():
        return
    if _reconcile_completed:
        return
    resolved_config = config if config is not None else journal_state.get_config()
    if resolved_config is not None:
        journal_module.initialize_for_config(resolved_config)
    snapshot = build_existing_config_snapshot()
    if not snapshot.reconciled:
        return
    # Lazy import: octobot_node.scheduler pulls octobot_flow → octobot.community (circular at import time).
    import octobot_node.scheduler as scheduler_module
    import octobot_node.scheduler.automations.automation_states_loader as automation_states_loader

    if not scheduler_module.is_initialized():
        return

    automation_ids: set[str] = set()
    running_automation_count = 0
    for wallet_id in collection_providers.AccountProvider.instance().list_collectable_wallet_ids():
        automation_states = await automation_states_loader.load_protocol_automation_states(
            wallet_id,
            statuses=None,
        )
        automation_ids.update(_distinct_automation_ids_from_states(automation_states))
        running_automation_count += sum(
            1
            for automation_state in automation_states
            if automation_state.status == protocol_models.WorkflowStatus.RUNNING
        )
    journal_recording.record_reconcile_completed(
        automation_count=len(automation_ids),
        running_automation_count=running_automation_count,
    )
    _reconcile_completed = True
