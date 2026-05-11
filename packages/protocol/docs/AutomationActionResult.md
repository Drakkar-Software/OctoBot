# AutomationActionResult

AutomationActionResult

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**updated_at** | **datetime** |  | 
**error_message** | [**AutomationActionResultErrorMessage**](AutomationActionResultErrorMessage.md) |  | [optional] 
**error_details** | **str** |  | [optional] 
**created_automation_id** | **str** |  | [optional] 
**result_type** | [**UserActionResultType**](UserActionResultType.md) |  | 

## Example

```python
from octobot_protocol.models.automation_action_result import AutomationActionResult

# TODO update the JSON string below
json = "{}"
# create an instance of AutomationActionResult from a JSON string
automation_action_result_instance = AutomationActionResult.from_json(json)
# print the JSON string representation of the object
print(AutomationActionResult.to_json())

# convert the object into a dict
automation_action_result_dict = automation_action_result_instance.to_dict()
# create an instance of AutomationActionResult from a dict
automation_action_result_from_dict = AutomationActionResult.from_dict(automation_action_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


