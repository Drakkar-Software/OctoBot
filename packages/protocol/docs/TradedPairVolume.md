# TradedPairVolume

Optional 24h volume for a traded pair. Empty object when volume was not requested.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**base_volume** | **float** | 24h base-currency volume. | [optional] 
**quote_volume** | **float** | 24h quote-currency volume. | [optional] 

## Example

```python
from octobot_protocol.models.traded_pair_volume import TradedPairVolume

# TODO update the JSON string below
json = "{}"
# create an instance of TradedPairVolume from a JSON string
traded_pair_volume_instance = TradedPairVolume.from_json(json)
# print the JSON string representation of the object
print(TradedPairVolume.to_json())

# convert the object into a dict
traded_pair_volume_dict = traded_pair_volume_instance.to_dict()
# create an instance of TradedPairVolume from a dict
traded_pair_volume_from_dict = TradedPairVolume.from_dict(traded_pair_volume_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


