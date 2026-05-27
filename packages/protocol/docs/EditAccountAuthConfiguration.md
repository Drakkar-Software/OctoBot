# EditAccountAuthConfiguration

EditAccountAuthConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**UserActionType**](UserActionType.md) | account_auth_edit | 
**id** | **str** |  | 
**configuration** | [**AccountAuthentication**](AccountAuthentication.md) |  | 

## Example

```python
from octobot_protocol.models.edit_account_auth_configuration import EditAccountAuthConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of EditAccountAuthConfiguration from a JSON string
edit_account_auth_configuration_instance = EditAccountAuthConfiguration.from_json(json)
# print the JSON string representation of the object
print(EditAccountAuthConfiguration.to_json())

# convert the object into a dict
edit_account_auth_configuration_dict = edit_account_auth_configuration_instance.to_dict()
# create an instance of EditAccountAuthConfiguration from a dict
edit_account_auth_configuration_from_dict = EditAccountAuthConfiguration.from_dict(edit_account_auth_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


