# AccountAuthActionResult

AccountAuthActionResult

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**updated_at** | **datetime** |  | 
**error_message** | [**AccountAuthActionResultErrorMessage**](AccountAuthActionResultErrorMessage.md) |  | [optional] 
**error_details** | **str** |  | [optional] 
**result_type** | [**UserActionResultType**](UserActionResultType.md) | account_auth | 

## Example

```python
from octobot_protocol.models.account_auth_action_result import AccountAuthActionResult

# TODO update the JSON string below
json = "{}"
# create an instance of AccountAuthActionResult from a JSON string
account_auth_action_result_instance = AccountAuthActionResult.from_json(json)
# print the JSON string representation of the object
print(AccountAuthActionResult.to_json())

# convert the object into a dict
account_auth_action_result_dict = account_auth_action_result_instance.to_dict()
# create an instance of AccountAuthActionResult from a dict
account_auth_action_result_from_dict = AccountAuthActionResult.from_dict(account_auth_action_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


