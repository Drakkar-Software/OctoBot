# DetailedAsset

DetailedAsset

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**symbol** | **str** |  | 
**total** | **float** |  | 
**available** | **float** |  | 

## Example

```python
from octobot_protocol.models.detailed_asset import DetailedAsset

# TODO update the JSON string below
json = "{}"
# create an instance of DetailedAsset from a JSON string
detailed_asset_instance = DetailedAsset.from_json(json)
# print the JSON string representation of the object
print(DetailedAsset.to_json())

# convert the object into a dict
detailed_asset_dict = detailed_asset_instance.to_dict()
# create an instance of DetailedAsset from a dict
detailed_asset_from_dict = DetailedAsset.from_dict(detailed_asset_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


