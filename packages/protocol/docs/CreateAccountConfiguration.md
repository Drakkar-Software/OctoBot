# CreateAccountConfiguration

CreateAccountConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | **str** |  | 
**configuration** | [**Account**](Account.md) |  | 

## Example

```python
from octobot_protocol.models.create_account_configuration import CreateAccountConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of CreateAccountConfiguration from a JSON string
create_account_configuration_instance = CreateAccountConfiguration.from_json(json)
# print the JSON string representation of the object
print(CreateAccountConfiguration.to_json())

# convert the object into a dict
create_account_configuration_dict = create_account_configuration_instance.to_dict()
# create an instance of CreateAccountConfiguration from a dict
create_account_configuration_from_dict = CreateAccountConfiguration.from_dict(create_account_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


