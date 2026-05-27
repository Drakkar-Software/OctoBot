# DeleteStrategyConfiguration

DeleteStrategyConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**UserActionType**](UserActionType.md) | strategy_delete | 
**id** | **str** |  | 

## Example

```python
from octobot_protocol.models.delete_strategy_configuration import DeleteStrategyConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of DeleteStrategyConfiguration from a JSON string
delete_strategy_configuration_instance = DeleteStrategyConfiguration.from_json(json)
# print the JSON string representation of the object
print(DeleteStrategyConfiguration.to_json())

# convert the object into a dict
delete_strategy_configuration_dict = delete_strategy_configuration_instance.to_dict()
# create an instance of DeleteStrategyConfiguration from a dict
delete_strategy_configuration_from_dict = DeleteStrategyConfiguration.from_dict(delete_strategy_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


