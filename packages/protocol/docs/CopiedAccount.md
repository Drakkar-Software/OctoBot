# CopiedAccount

CopiedAccount

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**updated_at** | **float** |  | 
**copied_assets** | [**List[CopiedAsset]**](CopiedAsset.md) |  | 
**orders** | [**List[Order]**](Order.md) |  | [optional] 
**positions** | [**List[Position]**](Position.md) |  | [optional] 
**historical_snapshots** | [**List[CopiedAccount]**](CopiedAccount.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.copied_account import CopiedAccount

# TODO update the JSON string below
json = "{}"
# create an instance of CopiedAccount from a JSON string
copied_account_instance = CopiedAccount.from_json(json)
# print the JSON string representation of the object
print(CopiedAccount.to_json())

# convert the object into a dict
copied_account_dict = copied_account_instance.to_dict()
# create an instance of CopiedAccount from a dict
copied_account_from_dict = CopiedAccount.from_dict(copied_account_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


