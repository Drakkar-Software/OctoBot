#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
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
import mock
import pytest
import datetime

import octobot.community
import octobot.community.supabase_backend.enums as enums


@pytest.fixture
def mock_supabase_client():
    client = octobot.community.CommunitySupabaseClient(
        "https://kfgrrr.supabase.co",
        "ccccccccccccccccccc.aaa.bbb",
        None,
    )
    yield client


@pytest.mark.asyncio
async def test_fetch_bot_nested_config_profile_data_if_any_invalid_inputs(mock_supabase_client):
    mock_supabase_client.table = mock.Mock()
    assert await mock_supabase_client.fetch_bot_nested_config_profile_data_if_any() is None
    mock_supabase_client.table.assert_not_called()

    # with master config
    assert await mock_supabase_client.fetch_bot_nested_config_profile_data_if_any(
        master_profile_config={enums.NestedProductConfigKeys.NESTED_CONFIG_ROOT.value: {}}
    ) is None
    mock_supabase_client.table.assert_not_called()

    with pytest.raises(TypeError):
        await mock_supabase_client.fetch_bot_nested_config_profile_data_if_any(
            master_profile_config={enums.NestedProductConfigKeys.NESTED_CONFIG_ROOT.value: {
                enums.NestedProductConfigKeys.SLUG.value: "plop"
            }}
        )
    mock_supabase_client.table.assert_called_once()
    mock_supabase_client.table.reset_mock()

    # with bot_config config
    assert await mock_supabase_client.fetch_bot_nested_config_profile_data_if_any(
        bot_config_options={enums.NestedProductConfigKeys.NESTED_CONFIG_ROOT.value: {}}
    ) is None
    mock_supabase_client.table.assert_not_called()

    with pytest.raises(TypeError):
        await mock_supabase_client.fetch_bot_nested_config_profile_data_if_any(
            bot_config_options={enums.NestedProductConfigKeys.NESTED_CONFIG_ROOT.value: {
                enums.NestedProductConfigKeys.SLUG.value: "plop"
            }}
        )
    mock_supabase_client.table.assert_called_once()
    mock_supabase_client.table.reset_mock()

    # with nested_config_id
    assert await mock_supabase_client.fetch_bot_nested_config_profile_data_if_any(
        nested_config_id=""
    ) is None
    mock_supabase_client.table.assert_not_called()

    with pytest.raises(TypeError):
        await mock_supabase_client.fetch_bot_nested_config_profile_data_if_any(
            nested_config_id="plop"
        )
    mock_supabase_client.table.assert_called_once()
    mock_supabase_client.table.reset_mock()

    # with index error
    assert await mock_supabase_client.fetch_bot_nested_config_profile_data_if_any(
        nested_config_id=""
    ) is None
    mock_supabase_client.table = mock.Mock(side_effect=IndexError)

    with pytest.raises(octobot.community.errors.InvalidBotConfigError):
        await mock_supabase_client.fetch_bot_nested_config_profile_data_if_any(
            nested_config_id="plop"
        )
    mock_supabase_client.table.assert_called_once()
    mock_supabase_client.table.reset_mock()


@pytest.mark.asyncio
async def test_fetch_bot_nested_config_profile_data_if_any_valid_inputs(mock_supabase_client):
    _execute_products_mock = mock.AsyncMock(
        return_value=mock.Mock(
            data = [{
                "id": "product_id-xyz",
                "slug": "slug-xyz",
                "attributes": "attributes-xyz",
                "current_config_id": "current_config_id-xyz",
                "product_config": {
                    "id": "product_config.id-xyz",
                    "config": "product_config.config-xyz",
                    "version": "product_config.version-xyz",
                },
            }]
        )
    )
    _execute_product_configs_mock = mock.AsyncMock(
        return_value=mock.Mock(
            data = [{
                "id": "id-xyz",
                "config" : "config-xyz",
                "version": "version-xyz",
                "product_config": {
                    "id": "product_config.id-xyz",
                    "slug": "product_config.slug-xyz",
                    "attributes": "product_config.attributes-xyz",
                    "current_config_id": "product_config.current_config_id-xyz",
                },
            }]
        )
    )
    def _select_mock(table):
        return mock.Mock(
            select=mock.Mock(
                return_value=mock.Mock(
                    eq=mock.Mock(return_value=mock.Mock(
                        execute=_execute_products_mock if table == "products" else _execute_product_configs_mock
                    ))
                )
            )
        )
    mock_supabase_client.table = mock.Mock(side_effect=_select_mock)

    # with master config => select from product slug
    config = await mock_supabase_client.fetch_bot_nested_config_profile_data_if_any(
        master_profile_config={enums.NestedProductConfigKeys.NESTED_CONFIG_ROOT.value: {
            enums.NestedProductConfigKeys.SLUG.value: "plop"
        }}
    )
    assert config == {
        'config': 'product_config.config-xyz',
        'id': 'product_config.id-xyz',
        'product': {'attributes': 'attributes-xyz', 'slug': 'slug-xyz', 'id': 'product_id-xyz'},
        'version': 'product_config.version-xyz'
    }
    mock_supabase_client.table.assert_called_once()
    _execute_products_mock.assert_called_once()
    _execute_products_mock.reset_mock()
    _execute_product_configs_mock.assert_not_called()
    mock_supabase_client.table.reset_mock()

    # with bot config => select from product slug
    config = await mock_supabase_client.fetch_bot_nested_config_profile_data_if_any(
        bot_config_options={enums.NestedProductConfigKeys.NESTED_CONFIG_ROOT.value: {
            enums.NestedProductConfigKeys.SLUG.value: "plop"
        }}
    )
    assert config == {
        'config': 'product_config.config-xyz',
        'id': 'product_config.id-xyz',
        'product': {'attributes': 'attributes-xyz', 'slug': 'slug-xyz', 'id': 'product_id-xyz'},
        'version': 'product_config.version-xyz'
    }
    mock_supabase_client.table.assert_called_once()
    _execute_products_mock.assert_called_once()
    _execute_products_mock.reset_mock()
    _execute_product_configs_mock.assert_not_called()
    mock_supabase_client.table.reset_mock()

    # with nested_config_id => select from product_configs
    config = await mock_supabase_client.fetch_bot_nested_config_profile_data_if_any(
        nested_config_id="plop"
    )
    assert config == {
        'config': 'config-xyz',
        'id': 'id-xyz',
        'product_config': {'attributes': 'product_config.attributes-xyz',
                           'current_config_id': 'product_config.current_config_id-xyz',
                           'slug': 'product_config.slug-xyz',
                           'id': 'product_config.id-xyz'},
        'version': 'version-xyz'
    }
    mock_supabase_client.table.assert_called_once()
    _execute_products_mock.assert_not_called()
    _execute_product_configs_mock.assert_called_once()
    _execute_product_configs_mock.reset_mock()
    mock_supabase_client.table.reset_mock()


@pytest.mark.asyncio
async def test_fetch_bot_profile_data_invalid_inputs(mock_supabase_client):
    with pytest.raises(octobot.community.errors.MissingBotConfigError):
        await mock_supabase_client.fetch_bot_profile_data("", {})
    with mock.patch.object(
        mock_supabase_client, "fetch_bot_nested_config_profile_data_if_any", mock.AsyncMock(side_effect=KeyError)
    ) as fetch_bot_nested_config_profile_data_if_any_mock:
        with pytest.raises(octobot.community.errors.MissingBotConfigError):
            await mock_supabase_client.fetch_bot_profile_data("", {})
        fetch_bot_nested_config_profile_data_if_any_mock.assert_not_called()


def test_get_formatted_time(mock_supabase_client):
    utc_ts = 1754636150 #  Friday, August 8, 2025 6:55:50 GMT (+00:00)
    assert mock_supabase_client.get_formatted_time(utc_ts) == "2025-08-08T06:55:50"
    utc_ts = 1704067200 #  Monday, January 1, 2024 0:00:00 GMT (+00:00)
    assert mock_supabase_client.get_formatted_time(utc_ts) == "2024-01-01T00:00:00"


def test_get_parsed_time(mock_supabase_client):
    # no timezone in parsed date: UTC timezone is forced
    assert mock_supabase_client.get_parsed_time("2025-08-08T06:55:50") == datetime.datetime(2025, 8, 8, 6, 55, 50, tzinfo=datetime.timezone.utc)
    assert mock_supabase_client.get_parsed_time("2025-08-08T06:55:50").timestamp() == 1754636150.0
    assert mock_supabase_client.get_parsed_time("2025-08-08T06:55:50.123") == datetime.datetime(2025, 8, 8, 6, 55, 50, 123000, tzinfo=datetime.timezone.utc)
    assert mock_supabase_client.get_parsed_time("2025-08-08T06:55:50.123+00:00").timestamp() == 1754636150.123
    # with timezone: timezone is kept
    assert mock_supabase_client.get_parsed_time("2025-08-08T06:55:50+00:00") == datetime.datetime(2025, 8, 8, 6, 55, 50, tzinfo=datetime.timezone.utc)
    assert mock_supabase_client.get_parsed_time("2025-08-08T06:55:50+00:00").timestamp() == 1754636150.0
    assert mock_supabase_client.get_parsed_time("2025-08-08T06:55:50.123+00:00") == datetime.datetime(2025, 8, 8, 6, 55, 50, 123000, tzinfo=datetime.timezone.utc)
    assert mock_supabase_client.get_parsed_time("2025-08-08T06:55:50.123+00:00").timestamp() == 1754636150.123
    # with non UTC timezone: timezone is kept
    assert mock_supabase_client.get_parsed_time("2025-08-08T06:55:50+02:00") == datetime.datetime(
        2025, 8, 8, 6, 55, 50, tzinfo=datetime.timezone(datetime.timedelta(hours=2))
    )
    assert mock_supabase_client.get_parsed_time("2025-08-08T06:55:50+02:00").timestamp() == 1754636150.0 - 2 * 3600
