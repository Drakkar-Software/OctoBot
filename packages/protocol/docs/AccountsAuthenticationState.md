# AccountsAuthenticationState

AccountsAuthenticationState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**account_authentication** | [**List[AccountAuthentication]**](AccountAuthentication.md) |  | 

## Example

```python
from octobot_protocol.models.accounts_authentication_state import AccountsAuthenticationState

# TODO update the JSON string below
json = "{}"
# create an instance of AccountsAuthenticationState from a JSON string
accounts_authentication_state_instance = AccountsAuthenticationState.from_json(json)
# print the JSON string representation of the object
print(AccountsAuthenticationState.to_json())

# convert the object into a dict
accounts_authentication_state_dict = accounts_authentication_state_instance.to_dict()
# create an instance of AccountsAuthenticationState from a dict
accounts_authentication_state_from_dict = AccountsAuthenticationState.from_dict(accounts_authentication_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


