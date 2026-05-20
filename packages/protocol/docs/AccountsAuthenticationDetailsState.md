# AccountsAuthenticationDetailsState

AccountsAuthenticationDetailsState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**details** | [**List[AccountAuthenticationDetails]**](AccountAuthenticationDetails.md) |  | 

## Example

```python
from octobot_protocol.models.accounts_authentication_details_state import AccountsAuthenticationDetailsState

# TODO update the JSON string below
json = "{}"
# create an instance of AccountsAuthenticationDetailsState from a JSON string
accounts_authentication_details_state_instance = AccountsAuthenticationDetailsState.from_json(json)
# print the JSON string representation of the object
print(AccountsAuthenticationDetailsState.to_json())

# convert the object into a dict
accounts_authentication_details_state_dict = accounts_authentication_details_state_instance.to_dict()
# create an instance of AccountsAuthenticationDetailsState from a dict
accounts_authentication_details_state_from_dict = AccountsAuthenticationDetailsState.from_dict(accounts_authentication_details_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


