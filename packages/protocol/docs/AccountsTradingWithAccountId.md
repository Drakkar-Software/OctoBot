# AccountsTradingWithAccountId

AccountsTradingWithAccountId

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**account_id** | **str** |  | 
**account_trading** | [**AccountTrading**](AccountTrading.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.accounts_trading_with_account_id import AccountsTradingWithAccountId

# TODO update the JSON string below
json = "{}"
# create an instance of AccountsTradingWithAccountId from a JSON string
accounts_trading_with_account_id_instance = AccountsTradingWithAccountId.from_json(json)
# print the JSON string representation of the object
print(AccountsTradingWithAccountId.to_json())

# convert the object into a dict
accounts_trading_with_account_id_dict = accounts_trading_with_account_id_instance.to_dict()
# create an instance of AccountsTradingWithAccountId from a dict
accounts_trading_with_account_id_from_dict = AccountsTradingWithAccountId.from_dict(accounts_trading_with_account_id_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


