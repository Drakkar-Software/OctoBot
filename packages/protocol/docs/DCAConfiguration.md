# DCAConfiguration

DCAConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**ActionConfigurationType**](ActionConfigurationType.md) | dca | 
**symbols** | **List[str]** |  | 
**entry_order_amount** | **str** | Amout to buy, can be in %t, %s, in q, in base, etc | 
**exit_limit_orders_price_percent** | **float** |  | 
**entry_limit_orders_price_percent** | **float** |  | 
**secondary_entry_orders_count** | **float** |  | [default to 0]
**secondary_entry_orders_amount** | **str** | Amout to buy, can be in %t, %s, in q, in base, etc | [default to '0%t']
**secondary_entry_orders_price_percent** | **float** |  | [default to 10]
**enable_stop_loss** | **bool** |  | [optional] [default to False]
**stop_loss_price_discount_percent** | **float** |  | [optional] [default to 10]
**trigger_mode** | **str** |  | [optional] [default to 'Maximum evaluators signals based']
**use_init_entry_orders** | **bool** |  | [optional] [default to True]
**max_asset_holding_percent** | **float** |  | [optional] [default to 50]
**strategies** | [**List[StrategyEvaluatorConfiguration]**](StrategyEvaluatorConfiguration.md) |  | 
**evaluators** | [**List[EvaluatorConfiguration]**](EvaluatorConfiguration.md) |  | 

## Example

```python
from octobot_protocol.models.dca_configuration import DCAConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of DCAConfiguration from a JSON string
dca_configuration_instance = DCAConfiguration.from_json(json)
# print the JSON string representation of the object
print(DCAConfiguration.to_json())

# convert the object into a dict
dca_configuration_dict = dca_configuration_instance.to_dict()
# create an instance of DCAConfiguration from a dict
dca_configuration_from_dict = DCAConfiguration.from_dict(dca_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


