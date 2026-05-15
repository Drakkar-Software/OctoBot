# StrategyReference

StrategyReference

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**version** | **str** |  | 
**emit_signals** | **bool** |  | [optional] [default to False]

## Example

```python
from octobot_protocol.models.strategy_reference import StrategyReference

# TODO update the JSON string below
json = "{}"
# create an instance of StrategyReference from a JSON string
strategy_reference_instance = StrategyReference.from_json(json)
# print the JSON string representation of the object
print(StrategyReference.to_json())

# convert the object into a dict
strategy_reference_dict = strategy_reference_instance.to_dict()
# create an instance of StrategyReference from a dict
strategy_reference_from_dict = StrategyReference.from_dict(strategy_reference_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


