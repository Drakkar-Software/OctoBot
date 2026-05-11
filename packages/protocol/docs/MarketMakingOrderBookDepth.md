# MarketMakingOrderBookDepth

Order book depth parameters (cumulated volume and daily volume fraction).

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**cumulated_volume_percent** | **float** |  | 
**percent_daily_trading_volume** | **float** |  | 

## Example

```python
from octobot_protocol.models.market_making_order_book_depth import MarketMakingOrderBookDepth

# TODO update the JSON string below
json = "{}"
# create an instance of MarketMakingOrderBookDepth from a JSON string
market_making_order_book_depth_instance = MarketMakingOrderBookDepth.from_json(json)
# print the JSON string representation of the object
print(MarketMakingOrderBookDepth.to_json())

# convert the object into a dict
market_making_order_book_depth_dict = market_making_order_book_depth_instance.to_dict()
# create an instance of MarketMakingOrderBookDepth from a dict
market_making_order_book_depth_from_dict = MarketMakingOrderBookDepth.from_dict(market_making_order_book_depth_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


