# HistoricalAssetsForTradingType

HistoricalAssetsForTradingType

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**trading_type** | [**TradingType**](TradingType.md) |  | 
**assets** | [**List[HistoricalAssetValue]**](HistoricalAssetValue.md) |  | 

## Example

```python
from octobot_protocol.models.historical_assets_for_trading_type import HistoricalAssetsForTradingType

# TODO update the JSON string below
json = "{}"
# create an instance of HistoricalAssetsForTradingType from a JSON string
historical_assets_for_trading_type_instance = HistoricalAssetsForTradingType.from_json(json)
# print the JSON string representation of the object
print(HistoricalAssetsForTradingType.to_json())

# convert the object into a dict
historical_assets_for_trading_type_dict = historical_assets_for_trading_type_instance.to_dict()
# create an instance of HistoricalAssetsForTradingType from a dict
historical_assets_for_trading_type_from_dict = HistoricalAssetsForTradingType.from_dict(historical_assets_for_trading_type_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


