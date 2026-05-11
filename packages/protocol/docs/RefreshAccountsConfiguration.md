# RefreshAccountsConfiguration

RefreshAccountsConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**ActionType**](ActionType.md) |  | 
**account_ids** | **List[str]** |  | [optional] 

## Example

```python
from octobot_protocol.models.refresh_accounts_configuration import RefreshAccountsConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of RefreshAccountsConfiguration from a JSON string
refresh_accounts_configuration_instance = RefreshAccountsConfiguration.from_json(json)
# print the JSON string representation of the object
print(RefreshAccountsConfiguration.to_json())

# convert the object into a dict
refresh_accounts_configuration_dict = refresh_accounts_configuration_instance.to_dict()
# create an instance of RefreshAccountsConfiguration from a dict
refresh_accounts_configuration_from_dict = RefreshAccountsConfiguration.from_dict(refresh_accounts_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


