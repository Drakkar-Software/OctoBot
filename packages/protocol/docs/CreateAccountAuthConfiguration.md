# CreateAccountAuthConfiguration

CreateAccountAuthConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**UserActionType**](UserActionType.md) | account_auth_create | 
**configuration** | [**AccountAuthentication**](AccountAuthentication.md) |  | 

## Example

```python
from octobot_protocol.models.create_account_auth_configuration import CreateAccountAuthConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of CreateAccountAuthConfiguration from a JSON string
create_account_auth_configuration_instance = CreateAccountAuthConfiguration.from_json(json)
# print the JSON string representation of the object
print(CreateAccountAuthConfiguration.to_json())

# convert the object into a dict
create_account_auth_configuration_dict = create_account_auth_configuration_instance.to_dict()
# create an instance of CreateAccountAuthConfiguration from a dict
create_account_auth_configuration_from_dict = CreateAccountAuthConfiguration.from_dict(create_account_auth_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


