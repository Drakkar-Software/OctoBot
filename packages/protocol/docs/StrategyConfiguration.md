# StrategyConfiguration

StrategyConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**emit_signals** | **bool** |  | [optional] [default to False]

## Example

```python
from octobot_protocol.models.strategy_configuration import StrategyConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of StrategyConfiguration from a JSON string
strategy_configuration_instance = StrategyConfiguration.from_json(json)
# print the JSON string representation of the object
print(StrategyConfiguration.to_json())

# convert the object into a dict
strategy_configuration_dict = strategy_configuration_instance.to_dict()
# create an instance of StrategyConfiguration from a dict
strategy_configuration_from_dict = StrategyConfiguration.from_dict(strategy_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


