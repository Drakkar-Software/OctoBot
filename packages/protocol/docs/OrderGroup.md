# OrderGroup

OrderGroup

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**type** | [**OrderGroupType**](OrderGroupType.md) |  | [optional] 
**active_order_swap_strategy** | [**ActiveOrderSwapStrategy**](ActiveOrderSwapStrategy.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.order_group import OrderGroup

# TODO update the JSON string below
json = "{}"
# create an instance of OrderGroup from a JSON string
order_group_instance = OrderGroup.from_json(json)
# print the JSON string representation of the object
print(OrderGroup.to_json())

# convert the object into a dict
order_group_dict = order_group_instance.to_dict()
# create an instance of OrderGroup from a dict
order_group_from_dict = OrderGroup.from_dict(order_group_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


