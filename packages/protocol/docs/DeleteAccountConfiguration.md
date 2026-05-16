# DeleteAccountConfiguration

DeleteAccountConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | **str** |  | 
**id** | **str** |  | 

## Example

```python
from octobot_protocol.models.delete_account_configuration import DeleteAccountConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of DeleteAccountConfiguration from a JSON string
delete_account_configuration_instance = DeleteAccountConfiguration.from_json(json)
# print the JSON string representation of the object
print(DeleteAccountConfiguration.to_json())

# convert the object into a dict
delete_account_configuration_dict = delete_account_configuration_instance.to_dict()
# create an instance of DeleteAccountConfiguration from a dict
delete_account_configuration_from_dict = DeleteAccountConfiguration.from_dict(delete_account_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


