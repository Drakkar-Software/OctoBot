# AutomationsState

AutomationsState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**automations** | [**List[AutomationState]**](AutomationState.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.automations_state import AutomationsState

# TODO update the JSON string below
json = "{}"
# create an instance of AutomationsState from a JSON string
automations_state_instance = AutomationsState.from_json(json)
# print the JSON string representation of the object
print(AutomationsState.to_json())

# convert the object into a dict
automations_state_dict = automations_state_instance.to_dict()
# create an instance of AutomationsState from a dict
automations_state_from_dict = AutomationsState.from_dict(automations_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


