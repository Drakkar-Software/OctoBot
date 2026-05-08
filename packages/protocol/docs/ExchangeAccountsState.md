# ExchangeAccountsState

ExchangeAccountsState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**accounts** | [**List[Account]**](Account.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.exchange_accounts_state import ExchangeAccountsState

# TODO update the JSON string below
json = "{}"
# create an instance of ExchangeAccountsState from a JSON string
exchange_accounts_state_instance = ExchangeAccountsState.from_json(json)
# print the JSON string representation of the object
print(ExchangeAccountsState.to_json())

# convert the object into a dict
exchange_accounts_state_dict = exchange_accounts_state_instance.to_dict()
# create an instance of ExchangeAccountsState from a dict
exchange_accounts_state_from_dict = ExchangeAccountsState.from_dict(exchange_accounts_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


