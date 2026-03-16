import contextlib
import asyncio

import octobot.community

import octobot_flow.entities


class CommunityRepository:
    def __init__(self, authenticator: octobot.community.CommunityAuthentication):
        self.authenticator: octobot.community.CommunityAuthentication = authenticator

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
