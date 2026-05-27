# AccountTradingState

AccountTradingState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**account_trading** | [**AccountTrading**](AccountTrading.md) |  | 

## Example

```python
from octobot_protocol.models.account_trading_state import AccountTradingState

# TODO update the JSON string below
json = "{}"
# create an instance of AccountTradingState from a JSON string
account_trading_state_instance = AccountTradingState.from_json(json)
# print the JSON string representation of the object
print(AccountTradingState.to_json())

# convert the object into a dict
account_trading_state_dict = account_trading_state_instance.to_dict()
# create an instance of AccountTradingState from a dict
account_trading_state_from_dict = AccountTradingState.from_dict(account_trading_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


