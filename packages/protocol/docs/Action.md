# Action

Action

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**action_type** | **str** |  | 
**status** | [**WorkflowStatus**](WorkflowStatus.md) |  | 
**dsl** | **str** |  | [optional] 
**configuration** | **Dict[str, object]** |  | [optional] 
**result** | **str** |  | [optional] 
**error** | **str** |  | [optional] 
**completed_at** | **datetime** |  | [optional] 

## Example

```python
from octobot_protocol.models.action import Action

# TODO update the JSON string below
json = "{}"
# create an instance of Action from a JSON string
action_instance = Action.from_json(json)
# print the JSON string representation of the object
print(Action.to_json())

# convert the object into a dict
action_dict = action_instance.to_dict()
# create an instance of Action from a dict
action_from_dict = Action.from_dict(action_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


