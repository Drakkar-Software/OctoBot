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


class TestExchangeTypeToTradingType:
    def test_maps_spot_exchange_type(self):
        assert (
            protocol_trading_mapping.EXCHANGE_TYPE_TO_TRADING_TYPE.get(
                trading_enums.ExchangeTypes.SPOT,
            )
            == protocol_models.TradingType.SPOT
        )

    def test_maps_future_exchange_type(self):
        assert (
            protocol_trading_mapping.EXCHANGE_TYPE_TO_TRADING_TYPE.get(
                trading_enums.ExchangeTypes.FUTURE,
            )
            == protocol_models.TradingType.FUTURES
        )

    def test_maps_margin_exchange_type(self):
        assert (
            protocol_trading_mapping.EXCHANGE_TYPE_TO_TRADING_TYPE.get(
                trading_enums.ExchangeTypes.MARGIN,
            )
            == protocol_models.TradingType.MARGIN
        )

    def test_maps_option_exchange_type(self):
        assert (
            protocol_trading_mapping.EXCHANGE_TYPE_TO_TRADING_TYPE.get(
                trading_enums.ExchangeTypes.OPTION,
            )
            == protocol_models.TradingType.OPTIONS
        )

    def test_is_bijection_of_trading_type_to_exchange_type(self):
        assert protocol_trading_mapping.EXCHANGE_TYPE_TO_TRADING_TYPE == {
            exchange_type: trading_type
            for trading_type, exchange_type in protocol_trading_mapping.TRADING_TYPE_TO_EXCHANGE_TYPE.items()
        }
