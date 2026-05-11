# UserDataState

UserDataState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**automations** | [**List[AutomationState]**](AutomationState.md) |  | [optional] 
**user_actions** | [**List[UserAction]**](UserAction.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.user_data_state import UserDataState

# TODO update the JSON string below
json = "{}"
# create an instance of UserDataState from a JSON string
user_data_state_instance = UserDataState.from_json(json)
# print the JSON string representation of the object
print(UserDataState.to_json())

# convert the object into a dict
user_data_state_dict = user_data_state_instance.to_dict()
# create an instance of UserDataState from a dict
user_data_state_from_dict = UserDataState.from_dict(user_data_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


