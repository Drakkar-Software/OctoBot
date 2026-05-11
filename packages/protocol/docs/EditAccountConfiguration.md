# EditAccountConfiguration

EditAccountConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**UserActionType**](UserActionType.md) | account_edit | 
**id** | **str** |  | 
**configuration** | [**Account**](Account.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.edit_account_configuration import EditAccountConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of EditAccountConfiguration from a JSON string
edit_account_configuration_instance = EditAccountConfiguration.from_json(json)
# print the JSON string representation of the object
print(EditAccountConfiguration.to_json())

# convert the object into a dict
edit_account_configuration_dict = edit_account_configuration_instance.to_dict()
# create an instance of EditAccountConfiguration from a dict
edit_account_configuration_from_dict = EditAccountConfiguration.from_dict(edit_account_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


