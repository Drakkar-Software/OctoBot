# UserActionsState

UserActionsState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**user_actions** | [**List[UserAction]**](UserAction.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.user_actions_state import UserActionsState

# TODO update the JSON string below
json = "{}"
# create an instance of UserActionsState from a JSON string
user_actions_state_instance = UserActionsState.from_json(json)
# print the JSON string representation of the object
print(UserActionsState.to_json())

# convert the object into a dict
user_actions_state_dict = user_actions_state_instance.to_dict()
# create an instance of UserActionsState from a dict
user_actions_state_from_dict = UserActionsState.from_dict(user_actions_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


