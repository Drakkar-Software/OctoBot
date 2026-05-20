# AccountAuthenticationDetails

AccountAuthenticationDetails

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**api_key** | **str** |  | [optional] 
**api_secret** | **str** |  | [optional] 
**api_passphrase** | **str** |  | [optional] 
**public_key** | **str** |  | [optional] 
**private_key** | **str** |  | [optional] 
**seed_phrase** | **str** |  | [optional] 

## Example

```python
from octobot_protocol.models.account_authentication_details import AccountAuthenticationDetails

# TODO update the JSON string below
json = "{}"
# create an instance of AccountAuthenticationDetails from a JSON string
account_authentication_details_instance = AccountAuthenticationDetails.from_json(json)
# print the JSON string representation of the object
print(AccountAuthenticationDetails.to_json())

# convert the object into a dict
account_authentication_details_dict = account_authentication_details_instance.to_dict()
# create an instance of AccountAuthenticationDetails from a dict
account_authentication_details_from_dict = AccountAuthenticationDetails.from_dict(account_authentication_details_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


