#  Agent seed sync collection idempotency tests.

import octobot_node.agent_seed.constants as demo_agent_seed_constants

import tools.agent_seed.operations.seed_sync as agent_seed_seed_sync


class TestWriteSyncCollectionsIdempotent:
    def test_write_sync_collections_twice_does_not_raise(self, tmp_path):
        user_folder = tmp_path / "agent-seed-user"
        user_folder.mkdir()
        user_id = demo_agent_seed_constants.DEMO_AGENT_SEED_USER_ID
        agent_seed_seed_sync.write_sync_collections(user_folder, user_id)
        agent_seed_seed_sync.write_sync_collections(user_folder, user_id)
