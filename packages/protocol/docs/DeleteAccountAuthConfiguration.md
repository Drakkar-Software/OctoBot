# DeleteAccountAuthConfiguration

DeleteAccountAuthConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**UserActionType**](UserActionType.md) | account_auth_delete | 
**id** | **str** |  | 

## Example

```python
from octobot_protocol.models.delete_account_auth_configuration import DeleteAccountAuthConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of DeleteAccountAuthConfiguration from a JSON string
delete_account_auth_configuration_instance = DeleteAccountAuthConfiguration.from_json(json)
# print the JSON string representation of the object
print(DeleteAccountAuthConfiguration.to_json())

# convert the object into a dict
delete_account_auth_configuration_dict = delete_account_auth_configuration_instance.to_dict()
# create an instance of DeleteAccountAuthConfiguration from a dict
delete_account_auth_configuration_from_dict = DeleteAccountAuthConfiguration.from_dict(delete_account_auth_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


