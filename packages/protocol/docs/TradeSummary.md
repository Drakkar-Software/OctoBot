# TradeSummary

TradeSummary

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**symbol** | **str** |  | 

## Example

```python
from octobot_protocol.models.trade_summary import TradeSummary

# TODO update the JSON string below
json = "{}"
# create an instance of TradeSummary from a JSON string
trade_summary_instance = TradeSummary.from_json(json)
# print the JSON string representation of the object
print(TradeSummary.to_json())

# convert the object into a dict
trade_summary_dict = trade_summary_instance.to_dict()
# create an instance of TradeSummary from a dict
trade_summary_from_dict = TradeSummary.from_dict(trade_summary_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


