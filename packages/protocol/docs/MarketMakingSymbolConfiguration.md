# MarketMakingSymbolConfiguration

MarketMakingSymbolConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**symbol** | **str** |  | 
**reference_price** | [**List[MarketMakingReferencePair]**](MarketMakingReferencePair.md) |  | 
**min_spread** | **float** | Minimum spread as a percentage (e.g. 0.5 for 0.5%). | 
**max_spread** | **float** | Maximum spread as a percentage. | 
**order_book_depth** | [**MarketMakingOrderBookDepth**](MarketMakingOrderBookDepth.md) |  | [optional] 
**scheduled_volume** | [**MarketMakingScheduledVolume**](MarketMakingScheduledVolume.md) |  | [optional] 
**stop_conditions** | [**MarketMakingStopConditions**](MarketMakingStopConditions.md) |  | [optional] 
**bids_count** | **float** |  | 
**asks_count** | **float** |  | 
**orders_distribution** | [**MarketMakingOrdersDistribution**](MarketMakingOrdersDistribution.md) |  | 
**funds_distribution** | [**MarketMakingFundsDistribution**](MarketMakingFundsDistribution.md) |  | 
**max_base_budget** | **float** | 0 means unlimited when supported. | [optional] 
**max_quote_budget** | **float** | 0 means unlimited when supported. | [optional] 
**min_base_budget** | **float** |  | [optional] 
**min_quote_budget** | **float** |  | [optional] 
**hedging_engine** | [**MarketMakingHedgingEngine**](MarketMakingHedgingEngine.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.market_making_symbol_configuration import MarketMakingSymbolConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of MarketMakingSymbolConfiguration from a JSON string
market_making_symbol_configuration_instance = MarketMakingSymbolConfiguration.from_json(json)
# print the JSON string representation of the object
print(MarketMakingSymbolConfiguration.to_json())

# convert the object into a dict
market_making_symbol_configuration_dict = market_making_symbol_configuration_instance.to_dict()
# create an instance of MarketMakingSymbolConfiguration from a dict
market_making_symbol_configuration_from_dict = MarketMakingSymbolConfiguration.from_dict(market_making_symbol_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


