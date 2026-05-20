# AccountTradingDetails

AccountTradingDetails

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**updated_at** | **datetime** |  | 
**orders** | [**List[Order]**](Order.md) |  | [optional] 
**trades** | [**List[Trade]**](Trade.md) |  | [optional] 
**positions** | [**List[Position]**](Position.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.account_trading_details import AccountTradingDetails

# TODO update the JSON string below
json = "{}"
# create an instance of AccountTradingDetails from a JSON string
account_trading_details_instance = AccountTradingDetails.from_json(json)
# print the JSON string representation of the object
print(AccountTradingDetails.to_json())

# convert the object into a dict
account_trading_details_dict = account_trading_details_instance.to_dict()
# create an instance of AccountTradingDetails from a dict
account_trading_details_from_dict = AccountTradingDetails.from_dict(account_trading_details_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


