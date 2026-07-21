# TradedPairsForExchange

Map of trading pair symbol to optional volume fields.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------

## Example

```python
from octobot_protocol.models.traded_pairs_for_exchange import TradedPairsForExchange

# TODO update the JSON string below
json = "{}"
# create an instance of TradedPairsForExchange from a JSON string
traded_pairs_for_exchange_instance = TradedPairsForExchange.from_json(json)
# print the JSON string representation of the object
print(TradedPairsForExchange.to_json())

# convert the object into a dict
traded_pairs_for_exchange_dict = traded_pairs_for_exchange_instance.to_dict()
# create an instance of TradedPairsForExchange from a dict
traded_pairs_for_exchange_from_dict = TradedPairsForExchange.from_dict(traded_pairs_for_exchange_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


