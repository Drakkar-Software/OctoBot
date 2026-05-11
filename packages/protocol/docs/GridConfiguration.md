# GridConfiguration

GridConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**ActionConfigurationType**](ActionConfigurationType.md) |  | 
**symbol** | **str** |  | 
**spread** | **float** |  | 
**increment** | **float** |  | 
**buy_count** | **float** |  | 
**sell_count** | **float** |  | 
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


