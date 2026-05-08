# CopiedAsset

CopiedAsset

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**total** | **float** |  | 
**available** | **float** |  | 
**ratio** | **float** |  | 

## Example

```python
from octobot_protocol.models.copied_asset import CopiedAsset

# TODO update the JSON string below
json = "{}"
# create an instance of CopiedAsset from a JSON string
copied_asset_instance = CopiedAsset.from_json(json)
# print the JSON string representation of the object
print(CopiedAsset.to_json())

# convert the object into a dict
copied_asset_dict = copied_asset_instance.to_dict()
# create an instance of CopiedAsset from a dict
copied_asset_from_dict = CopiedAsset.from_dict(copied_asset_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


