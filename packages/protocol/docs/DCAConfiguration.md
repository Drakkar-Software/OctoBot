# DCAConfiguration

DCAConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**ActionConfigurationType**](ActionConfigurationType.md) | dca | 
**symbols** | **List[str]** |  | 
**buy_orders_count** | **float** |  | 
**percent_amount_per_buy_order** | **float** |  | 
**profit_target_percent** | **float** |  | 
**buy_order_price_discount_percent** | **float** |  | 
**enable_stop_loss** | **bool** |  | [default to False]
**stop_loss_price_discount_percent** | **float** |  | 
**trigger_mode** | **str** |  | 
**use_init_entry_orders** | **bool** |  | [default to True]
**time_frames** | [**List[TimeFrame]**](TimeFrame.md) |  | 
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


