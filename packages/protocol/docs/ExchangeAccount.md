# ExchangeAccount

ExchangeAccount

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**exchange** | **str** |  | 
**remote_account_id** | **str** |  | 
**api_key** | **str** |  | 
**api_secret** | **str** |  | 
**api_passphrase** | **str** |  | [optional] 
**assets** | [**List[Asset]**](Asset.md) |  | [optional] 
**orders** | [**List[Order]**](Order.md) |  | [optional] 
**trades** | [**List[Trade]**](Trade.md) |  | [optional] 
**positions** | [**List[Position]**](Position.md) |  | [optional] 

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


