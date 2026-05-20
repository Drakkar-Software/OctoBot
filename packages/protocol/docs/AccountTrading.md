# AccountTrading

AccountTrading

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**updated_at** | **datetime** |  | 
**orders** | [**List[Order]**](Order.md) |  | [optional] 
**trades** | [**List[Trade]**](Trade.md) |  | [optional] 
**positions** | [**List[Position]**](Position.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.account_trading import AccountTrading

# TODO update the JSON string below
json = "{}"
# create an instance of AccountTrading from a JSON string
account_trading_instance = AccountTrading.from_json(json)
# print the JSON string representation of the object
print(AccountTrading.to_json())

# convert the object into a dict
account_trading_dict = account_trading_instance.to_dict()
# create an instance of AccountTrading from a dict
account_trading_from_dict = AccountTrading.from_dict(account_trading_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


