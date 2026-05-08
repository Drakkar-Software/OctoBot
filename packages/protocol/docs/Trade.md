# Trade

Trade

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**trade_id** | **str** |  | 
**type** | [**OrderType**](OrderType.md) |  | 
**symbol** | **str** |  | 
**side** | [**Side**](Side.md) |  | 
**quantity** | **float** |  | 
**price** | **float** |  | 
**status** | [**OrderStatus**](OrderStatus.md) |  | 
**executed_at** | **datetime** |  | 

## Example

```python
from octobot_protocol.models.trade import Trade

# TODO update the JSON string below
json = "{}"
# create an instance of Trade from a JSON string
trade_instance = Trade.from_json(json)
# print the JSON string representation of the object
print(Trade.to_json())

# convert the object into a dict
trade_dict = trade_instance.to_dict()
# create an instance of Trade from a dict
trade_from_dict = Trade.from_dict(trade_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


