# ActiveOrderSwapStrategy

ActiveOrderSwapStrategy

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | [**ActiveOrderSwapStrategyType**](ActiveOrderSwapStrategyType.md) |  | 
**trigger_price_configuration** | **object** |  | [optional] 
**timeout** | **float** |  | [optional] 

## Example

```python
from octobot_protocol.models.active_order_swap_strategy import ActiveOrderSwapStrategy

# TODO update the JSON string below
json = "{}"
# create an instance of ActiveOrderSwapStrategy from a JSON string
active_order_swap_strategy_instance = ActiveOrderSwapStrategy.from_json(json)
# print the JSON string representation of the object
print(ActiveOrderSwapStrategy.to_json())

# convert the object into a dict
active_order_swap_strategy_dict = active_order_swap_strategy_instance.to_dict()
# create an instance of ActiveOrderSwapStrategy from a dict
active_order_swap_strategy_from_dict = ActiveOrderSwapStrategy.from_dict(active_order_swap_strategy_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


