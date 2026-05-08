# GenericAccount

GenericAccount

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**assets** | [**List[Asset]**](Asset.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.generic_account import GenericAccount

# TODO update the JSON string below
json = "{}"
# create an instance of GenericAccount from a JSON string
generic_account_instance = GenericAccount.from_json(json)
# print the JSON string representation of the object
print(GenericAccount.to_json())

# convert the object into a dict
generic_account_dict = generic_account_instance.to_dict()
# create an instance of GenericAccount from a dict
generic_account_from_dict = GenericAccount.from_dict(generic_account_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


