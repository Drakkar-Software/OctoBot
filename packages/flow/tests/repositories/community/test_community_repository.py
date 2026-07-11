import mock

import octobot_flow.repositories.community.community_repository as community_repository_module


class TestUserIdToEvm:
    def test_user_id_to_evm_returns_none_when_user_id_is_none(self):
        assert community_repository_module.CommunityRepository.user_id_to_evm(None) is None

    def test_user_id_to_evm_returns_wallet_address(self):
        mock_wallet = mock.Mock(address="0xabc")
        mock_auth = mock.Mock(get_wallet_by_user_id=mock.Mock(return_value=mock_wallet))
        with mock.patch.object(
            community_repository_module.octobot.community.CommunityAuthentication,
            "instance",
            return_value=mock_auth,
        ):
            result = community_repository_module.CommunityRepository.user_id_to_evm("user_1")
        assert result == "0xabc"
        mock_auth.get_wallet_by_user_id.assert_called_once_with("user_1")

    def test_user_id_to_evm_returns_none_when_resolution_fails(self):
        mock_auth = mock.Mock(get_wallet_by_user_id=mock.Mock(side_effect=ValueError("not found")))
        with (
            mock.patch.object(
                community_repository_module.octobot.community.CommunityAuthentication,
                "instance",
                return_value=mock_auth,
            ),
            mock.patch.object(
                community_repository_module.octobot_commons.logging,
                "get_logger",
            ) as mock_get_logger,
        ):
            result = community_repository_module.CommunityRepository.user_id_to_evm("user_1")
        assert result is None
        mock_get_logger.return_value.warning.assert_called_once()
