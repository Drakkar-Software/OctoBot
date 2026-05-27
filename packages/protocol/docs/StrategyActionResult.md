# StrategyActionResult

StrategyActionResult

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**result_type** | [**UserActionResultType**](UserActionResultType.md) | strategy | 
**updated_at** | **datetime** |  | 
**error_message** | [**StrategyActionResultErrorMessage**](StrategyActionResultErrorMessage.md) |  | [optional] 
**error_details** | **str** |  | [optional] 

## Example

```python
from octobot_protocol.models.strategy_action_result import StrategyActionResult

# TODO update the JSON string below
json = "{}"
# create an instance of StrategyActionResult from a JSON string
strategy_action_result_instance = StrategyActionResult.from_json(json)
# print the JSON string representation of the object
print(StrategyActionResult.to_json())

# convert the object into a dict
strategy_action_result_dict = strategy_action_result_instance.to_dict()
# create an instance of StrategyActionResult from a dict
strategy_action_result_from_dict = StrategyActionResult.from_dict(strategy_action_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


