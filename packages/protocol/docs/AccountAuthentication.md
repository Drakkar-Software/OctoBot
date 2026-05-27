# AccountAuthentication

AccountAuthentication

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**updated_at** | **datetime** |  | [optional] 
**api_key** | **str** |  | [optional] 
**api_secret** | **str** |  | [optional] 
**api_passphrase** | **str** |  | [optional] 
**public_key** | **str** |  | [optional] 
**private_key** | **str** |  | [optional] 
**seed_phrase** | **str** |  | [optional] 

## Example

```python
from octobot_protocol.models.account_authentication import AccountAuthentication

# TODO update the JSON string below
json = "{}"
# create an instance of AccountAuthentication from a JSON string
account_authentication_instance = AccountAuthentication.from_json(json)
# print the JSON string representation of the object
print(AccountAuthentication.to_json())

# convert the object into a dict
account_authentication_dict = account_authentication_instance.to_dict()
# create an instance of AccountAuthentication from a dict
account_authentication_from_dict = AccountAuthentication.from_dict(account_authentication_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


