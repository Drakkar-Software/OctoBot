# MarketMakingScheduledVolume

Scheduled volume order sizing and timing in quote currency.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**min_amount** | **float** |  | [default to 0]
**max_amount** | **float** |  | [default to 0]
**min_interval_seconds** | **float** |  | [default to 0]
**max_interval_seconds** | **float** |  | [default to 0]

## Example

```python
from octobot_protocol.models.market_making_scheduled_volume import MarketMakingScheduledVolume

# TODO update the JSON string below
json = "{}"
# create an instance of MarketMakingScheduledVolume from a JSON string
market_making_scheduled_volume_instance = MarketMakingScheduledVolume.from_json(json)
# print the JSON string representation of the object
print(MarketMakingScheduledVolume.to_json())

# convert the object into a dict
market_making_scheduled_volume_dict = market_making_scheduled_volume_instance.to_dict()
# create an instance of MarketMakingScheduledVolume from a dict
market_making_scheduled_volume_from_dict = MarketMakingScheduledVolume.from_dict(market_making_scheduled_volume_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


