# EditStrategyConfiguration

EditStrategyConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**UserActionType**](UserActionType.md) | strategy_edit | 
**id** | **str** |  | 
**configuration** | [**Strategy**](Strategy.md) |  | 

## Example

```python
from octobot_protocol.models.edit_strategy_configuration import EditStrategyConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of EditStrategyConfiguration from a JSON string
edit_strategy_configuration_instance = EditStrategyConfiguration.from_json(json)
# print the JSON string representation of the object
print(EditStrategyConfiguration.to_json())

# convert the object into a dict
edit_strategy_configuration_dict = edit_strategy_configuration_instance.to_dict()
# create an instance of EditStrategyConfiguration from a dict
edit_strategy_configuration_from_dict = EditStrategyConfiguration.from_dict(edit_strategy_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


