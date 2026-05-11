# AccountActionResult

AccountActionResult

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**updated_at** | **datetime** |  | 
**error_message** | [**AccountActionResultErrorMessage**](AccountActionResultErrorMessage.md) |  | [optional] 
**error_details** | **str** |  | [optional] 
**result_type** | [**UserActionResultType**](UserActionResultType.md) |  | 

## Example

```python
from octobot_protocol.models.account_action_result import AccountActionResult

# TODO update the JSON string below
json = "{}"
# create an instance of AccountActionResult from a JSON string
account_action_result_instance = AccountActionResult.from_json(json)
# print the JSON string representation of the object
print(AccountActionResult.to_json())

# convert the object into a dict
account_action_result_dict = account_action_result_instance.to_dict()
# create an instance of AccountActionResult from a dict
account_action_result_from_dict = AccountActionResult.from_dict(account_action_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


