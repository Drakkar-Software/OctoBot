import contextlib
import asyncio
import typing

import octobot.community
import octobot_commons.logging

import octobot_sync.client
import octobot_flow.entities
import octobot_flow.errors


class CommunityRepository:
    def __init__(self, authenticator: octobot.community.CommunityAuthentication, wallet_address: typing.Optional[str] = None):
        self.authenticator: octobot.community.CommunityAuthentication = authenticator
        self.wallet_address: typing.Optional[str] = wallet_address

    @classmethod
    def from_community_repository(cls, other_repository: "CommunityRepository") -> typing.Self:
        return cls(other_repository.authenticator, other_repository.wallet_address)

    @staticmethod
    def user_id_to_evm(user_id: typing.Optional[str]) -> typing.Optional[str]:
        """Return the EVM wallet address for a Starfish *user_id*, or None if unresolvable.

        The community repository (used inside OctoBotActionsJob) requires the EVM wallet
        address for the community sync client.  We store Starfish user_id in Task.user_id
        (the sync-core identity), so we must translate back to the EVM address at the
        automation-job boundary.
        """
        if user_id is None:
            return None
        try:
            return octobot.community.CommunityAuthentication.instance().get_wallet_by_user_id(
                user_id
            ).address
        except Exception as err:
            octobot_commons.logging.get_logger("CommunityRepository").warning(
                f"Could not resolve EVM address for user_id={user_id!r}: {err}"
            )
            return None

    async def insert_bot_logs(self, log_data: list[octobot.community.BotLogData]):
        await asyncio.gather(
            *[
                self.authenticator.supabase_client.insert_bot_log(
                    self.authenticator.user_account.bot_id,
                    log_data.log_type,
                    log_data.content
                )
                for log_data in log_data
            ]
        )

    @contextlib.contextmanager
    def automation_context(self, automation: octobot_flow.entities.AutomationDetails):
        previous_bot_id = self.authenticator.user_account.bot_id
        try:
            self.authenticator.user_account.bot_id = automation.metadata.automation_id # type: ignore
            yield
        finally:
            self.authenticator.user_account.bot_id = previous_bot_id # type: ignore

    def _get_sync_client(self) -> octobot_sync.client.StarfishClient:
        if self.wallet_address is None:
            raise octobot_flow.errors.WalletNotInitializedError(
                "Wallet not initialized: no wallet address provided"
            )
        return self.authenticator.get_sync_client_for_address(self.wallet_address)
