# GridConfiguration

GridConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**ActionConfigurationType**](ActionConfigurationType.md) | grid | 
**symbol** | **str** |  | 
**spread** | **float** | Price difference between the closest buy and sell orders. Denominated in the quote currency (600 for a 600 USDT spread on BTC/USDT). | 
**increment** | **float** | Price difference between two orders of the same side. Denominated in the quote currency (200 for a 200 USDT spread on BTC/USDT). | 
**buy_count** | **float** | Number of initial buy orders to create. Make sure to have enough funds to create that many orders. | 
**sell_count** | **float** | Number of initial sell orders to create. Make sure to have enough funds to create that many orders. | 
**enable_trailing_up** | **bool** |  | [default to True]
**enable_trailing_down** | **bool** |  | [default to False]
**order_by_order_trailing** | **bool** |  | [default to True]

## Example

```python
from octobot_protocol.models.grid_configuration import GridConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of GridConfiguration from a JSON string
grid_configuration_instance = GridConfiguration.from_json(json)
# print the JSON string representation of the object
print(GridConfiguration.to_json())

# convert the object into a dict
grid_configuration_dict = grid_configuration_instance.to_dict()
# create an instance of GridConfiguration from a dict
grid_configuration_from_dict = GridConfiguration.from_dict(grid_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


