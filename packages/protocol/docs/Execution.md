# Execution

One run of an automation. Append-only; the full history of an automation lives on AutomationState.executions.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**automation_id** | **str** |  | 
**reason** | **str** | Free-form why this run was triggered (e.g. &#39;user pulled to refresh&#39;, &#39;tick 9am&#39;, &#39;price-alert:BTC&#39;). | 
**started_at** | **int** | Epoch milliseconds when the run started. | 
**completed_at** | **int** | Epoch milliseconds when the run reached a terminal status. | [optional] 
**status** | [**TaskStatus**](TaskStatus.md) |  | 
**input** | **Dict[str, object]** | JSON snapshot of the state passed into the run. | [optional] 
**result** | **Dict[str, object]** | JSON snapshot of what the automation returned on success. | [optional] 
**error** | [**ExecutionError**](ExecutionError.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.execution import Execution

# TODO update the JSON string below
json = "{}"
# create an instance of Execution from a JSON string
execution_instance = Execution.from_json(json)
# print the JSON string representation of the object
print(Execution.to_json())

# convert the object into a dict
execution_dict = execution_instance.to_dict()
# create an instance of Execution from a dict
execution_from_dict = Execution.from_dict(execution_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


