# OrderSummary

OrderSummary

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**symbol** | **str** |  | 

## Example

```python
from octobot_protocol.models.order_summary import OrderSummary

# TODO update the JSON string below
json = "{}"
# create an instance of OrderSummary from a JSON string
order_summary_instance = OrderSummary.from_json(json)
# print the JSON string representation of the object
print(OrderSummary.to_json())

# convert the object into a dict
order_summary_dict = order_summary_instance.to_dict()
# create an instance of OrderSummary from a dict
order_summary_from_dict = OrderSummary.from_dict(order_summary_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


