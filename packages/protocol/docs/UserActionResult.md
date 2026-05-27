# UserActionResult


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**updated_at** | **datetime** |  | 
**error_message** | [**AccountAuthActionResultErrorMessage**](AccountAuthActionResultErrorMessage.md) |  | [optional] 
**error_details** | **str** |  | [optional] 
**created_automation_id** | **str** |  | [optional] 
**result_type** | [**UserActionResultType**](UserActionResultType.md) | account_auth | 

## Example

```python
from octobot_protocol.models.user_action_result import UserActionResult

# TODO update the JSON string below
json = "{}"
# create an instance of UserActionResult from a JSON string
user_action_result_instance = UserActionResult.from_json(json)
# print the JSON string representation of the object
print(UserActionResult.to_json())

# convert the object into a dict
user_action_result_dict = user_action_result_instance.to_dict()
# create an instance of UserActionResult from a dict
user_action_result_from_dict = UserActionResult.from_dict(user_action_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


