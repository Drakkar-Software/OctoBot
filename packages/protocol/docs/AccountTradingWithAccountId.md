# AccountTradingWithAccountId

AccountTradingWithAccountId

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**account_id** | **str** |  | 
**account_trading** | [**AccountTrading**](AccountTrading.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.account_trading_with_account_id import AccountTradingWithAccountId

# TODO update the JSON string below
json = "{}"
# create an instance of AccountTradingWithAccountId from a JSON string
account_trading_with_account_id_instance = AccountTradingWithAccountId.from_json(json)
# print the JSON string representation of the object
print(AccountTradingWithAccountId.to_json())

# convert the object into a dict
account_trading_with_account_id_dict = account_trading_with_account_id_instance.to_dict()
# create an instance of AccountTradingWithAccountId from a dict
account_trading_with_account_id_from_dict = AccountTradingWithAccountId.from_dict(account_trading_with_account_id_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


