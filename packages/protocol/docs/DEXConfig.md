# DEXConfig

DEXConfig

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**chain_id** | **str** |  | 
**dex_id** | **str** |  | 
**base_token_addresses** | **List[str]** |  | [optional] 
**quote_token_addresses** | **List[str]** |  | [optional] 

## Example

```python
from octobot_protocol.models.dex_config import DEXConfig

# TODO update the JSON string below
json = "{}"
# create an instance of DEXConfig from a JSON string
dex_config_instance = DEXConfig.from_json(json)
# print the JSON string representation of the object
print(DEXConfig.to_json())

# convert the object into a dict
dex_config_dict = dex_config_instance.to_dict()
# create an instance of DEXConfig from a dict
dex_config_from_dict = DEXConfig.from_dict(dex_config_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


