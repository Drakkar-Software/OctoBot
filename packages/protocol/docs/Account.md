# Account

Account

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**account_type** | [**AccountType**](AccountType.md) |  | 
**name** | **str** |  | 
**is_simulated** | **bool** |  | 
**description** | **str** |  | [optional] 
**created_at** | **datetime** |  | [optional] 
**updated_at** | **datetime** |  | [optional] 
**exchange_account** | [**ExchangeAccount**](ExchangeAccount.md) |  | [optional] 
**blockchain_account** | [**BlockchainAccount**](BlockchainAccount.md) |  | [optional] 
**generic_account** | [**GenericAccount**](GenericAccount.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.account import Account

# TODO update the JSON string below
json = "{}"
# create an instance of Account from a JSON string
account_instance = Account.from_json(json)
# print the JSON string representation of the object
print(Account.to_json())

# convert the object into a dict
account_dict = account_instance.to_dict()
# create an instance of Account from a dict
account_from_dict = Account.from_dict(account_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


