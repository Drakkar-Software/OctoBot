# AssetAccount

A manually-entered, single tracked non-liquid asset (a watch, a car, real estate, and similar).

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**account_type** | [**AccountType**](AccountType.md) | asset | 
**asset_type** | **str** |  | [optional] 
**cost_basis** | **float** |  | [optional] 

## Example

```python
from octobot_protocol.models.asset_account import AssetAccount

# TODO update the JSON string below
json = "{}"
# create an instance of AssetAccount from a JSON string
asset_account_instance = AssetAccount.from_json(json)
# print the JSON string representation of the object
print(AssetAccount.to_json())

# convert the object into a dict
asset_account_dict = asset_account_instance.to_dict()
# create an instance of AssetAccount from a dict
asset_account_from_dict = AssetAccount.from_dict(asset_account_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


