# MarketMakingStopConditions

Optional holdings and volatility thresholds used for automations / stop behavior.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**min_base_holding** | **float** |  | [optional] [default to 0]
**min_quote_holding** | **float** |  | [optional] [default to 0]
**max_positive_percent_price_change** | **float** |  | [optional] [default to 0]
**max_negative_percent_price_change** | **float** |  | [optional] [default to 0]
**average_price_counted_minutes** | **float** | Minutes window for average price when evaluating volatility stops. | [optional] [default to 60]

## Example

```python
from octobot_protocol.models.market_making_stop_conditions import MarketMakingStopConditions

# TODO update the JSON string below
json = "{}"
# create an instance of MarketMakingStopConditions from a JSON string
market_making_stop_conditions_instance = MarketMakingStopConditions.from_json(json)
# print the JSON string representation of the object
print(MarketMakingStopConditions.to_json())

# convert the object into a dict
market_making_stop_conditions_dict = market_making_stop_conditions_instance.to_dict()
# create an instance of MarketMakingStopConditions from a dict
market_making_stop_conditions_from_dict = MarketMakingStopConditions.from_dict(market_making_stop_conditions_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


