# AccountState

AccountState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**permissions** | [**List[AccountPermission]**](AccountPermission.md) |  | [optional] 
**status** | [**AccountStatus**](AccountStatus.md) |  | 
**message** | [**AccountStatusMessage**](AccountStatusMessage.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.account_state import AccountState

# TODO update the JSON string below
json = "{}"
# create an instance of AccountState from a JSON string
account_state_instance = AccountState.from_json(json)
# print the JSON string representation of the object
print(AccountState.to_json())

# convert the object into a dict
account_state_dict = account_state_instance.to_dict()
# create an instance of AccountState from a dict
account_state_from_dict = AccountState.from_dict(account_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


