# SignalPriorityActionExecutionResult

SignalPriorityActionExecutionResult

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**priority_action_id** | **str** |  | 
**error_status** | **str** |  | [optional] 
**error_message** | **str** |  | [optional] 

## Example

```python
from octobot_protocol.models.signal_priority_action_execution_result import SignalPriorityActionExecutionResult

# TODO update the JSON string below
json = "{}"
# create an instance of SignalPriorityActionExecutionResult from a JSON string
signal_priority_action_execution_result_instance = SignalPriorityActionExecutionResult.from_json(json)
# print the JSON string representation of the object
print(SignalPriorityActionExecutionResult.to_json())

# convert the object into a dict
signal_priority_action_execution_result_dict = signal_priority_action_execution_result_instance.to_dict()
# create an instance of SignalPriorityActionExecutionResult from a dict
signal_priority_action_execution_result_from_dict = SignalPriorityActionExecutionResult.from_dict(signal_priority_action_execution_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


