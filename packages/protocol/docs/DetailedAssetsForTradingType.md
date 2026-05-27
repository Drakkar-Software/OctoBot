# DetailedAssetsForTradingType

DetailedAssetsForTradingType

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**trading_type** | [**TradingType**](TradingType.md) |  | 
**assets** | [**List[DetailedAsset]**](DetailedAsset.md) |  | 

## Example

```python
from octobot_protocol.models.detailed_assets_for_trading_type import DetailedAssetsForTradingType

# TODO update the JSON string below
json = "{}"
# create an instance of DetailedAssetsForTradingType from a JSON string
detailed_assets_for_trading_type_instance = DetailedAssetsForTradingType.from_json(json)
# print the JSON string representation of the object
print(DetailedAssetsForTradingType.to_json())

# convert the object into a dict
detailed_assets_for_trading_type_dict = detailed_assets_for_trading_type_instance.to_dict()
# create an instance of DetailedAssetsForTradingType from a dict
detailed_assets_for_trading_type_from_dict = DetailedAssetsForTradingType.from_dict(detailed_assets_for_trading_type_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


