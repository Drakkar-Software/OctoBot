# ExecutionError

Serialized error captured for a failed Execution.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | [optional] 
**message** | **str** |  | 
**stack** | **str** |  | [optional] 

## Example

```python
from octobot_protocol.models.execution_error import ExecutionError

# TODO update the JSON string below
json = "{}"
# create an instance of ExecutionError from a JSON string
execution_error_instance = ExecutionError.from_json(json)
# print the JSON string representation of the object
print(ExecutionError.to_json())

# convert the object into a dict
execution_error_dict = execution_error_instance.to_dict()
# create an instance of ExecutionError from a dict
execution_error_from_dict = ExecutionError.from_dict(execution_error_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


