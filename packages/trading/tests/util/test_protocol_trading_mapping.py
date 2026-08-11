#  Drakkar-Software OctoBot-Trading

import octobot_protocol.models as protocol_models
import octobot_trading.enums as trading_enums
import octobot_trading.util.protocol_trading_mapping as protocol_trading_mapping


class TestTradingTypeToExchangeType:
    def test_maps_spot_trading_type(self):
        assert (
            protocol_trading_mapping.TRADING_TYPE_TO_EXCHANGE_TYPE.get(
                protocol_models.TradingType.SPOT,
            )
            == trading_enums.ExchangeTypes.SPOT
        )


class TestApiKeyRightToAccountPermission:
    def test_maps_known_api_key_rights_to_account_permissions(self):
        account_permissions = [
            protocol_trading_mapping.API_KEY_RIGHT_TO_ACCOUNT_PERMISSION.get(api_key_right)
            for api_key_right in [
                trading_enums.APIKeyRights.READING,
                trading_enums.APIKeyRights.SPOT_TRADING,
                trading_enums.APIKeyRights.FUTURES_TRADING,
                trading_enums.APIKeyRights.WITHDRAWALS,
                trading_enums.APIKeyRights.MARGIN_TRADING,
            ]
            if protocol_trading_mapping.API_KEY_RIGHT_TO_ACCOUNT_PERMISSION.get(api_key_right) is not None
        ]
        assert account_permissions == [
            protocol_models.AccountPermission.READ,
            protocol_models.AccountPermission.SPOT_TRADING,
            protocol_models.AccountPermission.FUTURES_TRADING,
            protocol_models.AccountPermission.WITHDRAW,
        ]


class TestOptimisticApiKeyRightsWhenPermissionsUnsupported:
    def test_contains_expected_rights(self):
        assert protocol_trading_mapping.OPTIMISTIC_API_KEY_RIGHTS_WHEN_PERMISSIONS_UNSUPPORTED == [
            trading_enums.APIKeyRights.READING,
            trading_enums.APIKeyRights.SPOT_TRADING,
            trading_enums.APIKeyRights.FUTURES_TRADING,
        ]
