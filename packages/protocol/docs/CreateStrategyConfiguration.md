# CreateStrategyConfiguration

CreateStrategyConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**UserActionType**](UserActionType.md) | strategy_create | 
**configuration** | [**Strategy**](Strategy.md) |  | 

## Example

```python
from octobot_protocol.models.create_strategy_configuration import CreateStrategyConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of CreateStrategyConfiguration from a JSON string
create_strategy_configuration_instance = CreateStrategyConfiguration.from_json(json)
# print the JSON string representation of the object
print(CreateStrategyConfiguration.to_json())

# convert the object into a dict
create_strategy_configuration_dict = create_strategy_configuration_instance.to_dict()
# create an instance of CreateStrategyConfiguration from a dict
create_strategy_configuration_from_dict = CreateStrategyConfiguration.from_dict(create_strategy_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


