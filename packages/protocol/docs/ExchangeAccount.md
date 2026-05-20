# ExchangeAccount

ExchangeAccount

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**account_type** | [**AccountType**](AccountType.md) | exchange | 
**trading_type** | [**TradingType**](TradingType.md) |  | 
**exchange** | **str** |  | 
**remote_account_id** | **str** |  | 

## Example

```python
from octobot_protocol.models.exchange_account import ExchangeAccount

# TODO update the JSON string below
json = "{}"
# create an instance of ExchangeAccount from a JSON string
exchange_account_instance = ExchangeAccount.from_json(json)
# print the JSON string representation of the object
print(ExchangeAccount.to_json())

# convert the object into a dict
exchange_account_dict = exchange_account_instance.to_dict()
# create an instance of ExchangeAccount from a dict
exchange_account_from_dict = ExchangeAccount.from_dict(exchange_account_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


