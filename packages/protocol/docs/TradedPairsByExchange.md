# TradedPairsByExchange

Map of exchange internal name to traded pairs (and optional volumes).

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------

## Example

```python
from octobot_protocol.models.traded_pairs_by_exchange import TradedPairsByExchange

# TODO update the JSON string below
json = "{}"
# create an instance of TradedPairsByExchange from a JSON string
traded_pairs_by_exchange_instance = TradedPairsByExchange.from_json(json)
# print the JSON string representation of the object
print(TradedPairsByExchange.to_json())

# convert the object into a dict
traded_pairs_by_exchange_dict = traded_pairs_by_exchange_instance.to_dict()
# create an instance of TradedPairsByExchange from a dict
traded_pairs_by_exchange_from_dict = TradedPairsByExchange.from_dict(traded_pairs_by_exchange_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


