# MarketMakingReferencePair

Reference price source for market making (exchange pair, weighting, and optional formula).

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**exchange** | **str** | Exchange id, or a sentinel such as local exchange price when supported by the trading mode. | 
**pair** | **str** |  | 
**weight** | **float** |  | [optional] 
**formula** | **str** | Optional formula overriding the default latest price for this source. | [optional] 
**time_frame** | [**TimeFrame**](TimeFrame.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.market_making_reference_pair import MarketMakingReferencePair

# TODO update the JSON string below
json = "{}"
# create an instance of MarketMakingReferencePair from a JSON string
market_making_reference_pair_instance = MarketMakingReferencePair.from_json(json)
# print the JSON string representation of the object
print(MarketMakingReferencePair.to_json())

# convert the object into a dict
market_making_reference_pair_dict = market_making_reference_pair_instance.to_dict()
# create an instance of MarketMakingReferencePair from a dict
market_making_reference_pair_from_dict = MarketMakingReferencePair.from_dict(market_making_reference_pair_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


