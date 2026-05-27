# AccountsState

AccountsState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**accounts** | [**List[Account]**](Account.md) |  | [optional] 
**exchange_configs** | [**List[ExchangeConfig]**](ExchangeConfig.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.accounts_state import AccountsState

# TODO update the JSON string below
json = "{}"
# create an instance of AccountsState from a JSON string
accounts_state_instance = AccountsState.from_json(json)
# print the JSON string representation of the object
print(AccountsState.to_json())

# convert the object into a dict
accounts_state_dict = accounts_state_instance.to_dict()
# create an instance of AccountsState from a dict
accounts_state_from_dict = AccountsState.from_dict(accounts_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


