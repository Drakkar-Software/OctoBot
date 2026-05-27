# UserActionConfiguration


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**UserActionType**](UserActionType.md) | accounts_refresh | 
**configuration** | [**ExchangeConfig**](ExchangeConfig.md) |  | 
**id** | **str** |  | 
**account_ids** | **List[str]** |  | [optional] 

## Example

```python
from octobot_protocol.models.user_action_configuration import UserActionConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of UserActionConfiguration from a JSON string
user_action_configuration_instance = UserActionConfiguration.from_json(json)
# print the JSON string representation of the object
print(UserActionConfiguration.to_json())

# convert the object into a dict
user_action_configuration_dict = user_action_configuration_instance.to_dict()
# create an instance of UserActionConfiguration from a dict
user_action_configuration_from_dict = UserActionConfiguration.from_dict(user_action_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


