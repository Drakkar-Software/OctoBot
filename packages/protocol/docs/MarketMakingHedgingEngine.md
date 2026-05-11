# MarketMakingHedgingEngine

Optional cross-exchange hedging configuration.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**average_price_counted_minutes** | **float** |  | [optional] [default to 60]
**hedging_engine_type** | **str** |  | [optional] 
**hedging_exchange** | **str** |  | [optional] 
**hedging_max_loss_threshold** | **float** |  | [optional] [default to 0]
**hedging_profit_threshold** | **float** |  | [optional] [default to 0]
**max_negative_percent_price_change** | **float** |  | [optional] [default to 0]
**max_positive_percent_price_change** | **float** |  | [optional] [default to 0]

## Example

```python
from octobot_protocol.models.market_making_hedging_engine import MarketMakingHedgingEngine

# TODO update the JSON string below
json = "{}"
# create an instance of MarketMakingHedgingEngine from a JSON string
market_making_hedging_engine_instance = MarketMakingHedgingEngine.from_json(json)
# print the JSON string representation of the object
print(MarketMakingHedgingEngine.to_json())

# convert the object into a dict
market_making_hedging_engine_dict = market_making_hedging_engine_instance.to_dict()
# create an instance of MarketMakingHedgingEngine from a dict
market_making_hedging_engine_from_dict = MarketMakingHedgingEngine.from_dict(market_making_hedging_engine_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


