# Order

Order

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**symbol** | **str** |  | 
**price** | **float** |  | 
**quantity** | **float** |  | 
**filled** | **float** |  | 
**exchange_id** | **str** |  | 
**side** | [**Side**](Side.md) |  | 
**type** | [**OrderType**](OrderType.md) |  | 
**trigger_above** | **bool** |  | [optional] 
**reduce_only** | **bool** |  | [optional] 
**is_active** | **bool** |  | [optional] 
**status** | [**OrderStatus**](OrderStatus.md) |  | 
**created_at** | **datetime** |  | 
**entries** | **List[str]** |  | [optional] 
**update_with_triggering_order_fees** | **bool** |  | [optional] 
**order_group** | [**OrderGroup**](OrderGroup.md) |  | [optional] 
**trailing_profile** | [**TrailingProfile**](TrailingProfile.md) |  | [optional] 
**cancel_policy** | [**CancelPolicy**](CancelPolicy.md) |  | [optional] 
**chained_orders** | [**List[Order]**](Order.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.order import Order

# TODO update the JSON string below
json = "{}"
# create an instance of Order from a JSON string
order_instance = Order.from_json(json)
# print the JSON string representation of the object
print(Order.to_json())

# convert the object into a dict
order_dict = order_instance.to_dict()
# create an instance of Order from a dict
order_from_dict = Order.from_dict(order_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


