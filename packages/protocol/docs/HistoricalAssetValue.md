# HistoricalAssetValue

HistoricalAssetValue

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**symbol** | **str** |  | 
**holdings** | **float** |  | 
**value** | **float** |  | 

## Example

```python
from octobot_protocol.models.historical_asset_value import HistoricalAssetValue

# TODO update the JSON string below
json = "{}"
# create an instance of HistoricalAssetValue from a JSON string
historical_asset_value_instance = HistoricalAssetValue.from_json(json)
# print the JSON string representation of the object
print(HistoricalAssetValue.to_json())

# convert the object into a dict
historical_asset_value_dict = historical_asset_value_instance.to_dict()
# create an instance of HistoricalAssetValue from a dict
historical_asset_value_from_dict = HistoricalAssetValue.from_dict(historical_asset_value_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


