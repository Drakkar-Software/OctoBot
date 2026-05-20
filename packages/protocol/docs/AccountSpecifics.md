# AccountSpecifics


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**account_type** | [**AccountType**](AccountType.md) | generic | 
**trading_type** | [**TradingType**](TradingType.md) |  | 
**exchange** | **str** |  | 
**remote_account_id** | **str** |  | 
**blockchain** | **str** |  | 
**network** | **str** |  | [optional] 

## Example

```python
from octobot_protocol.models.account_specifics import AccountSpecifics

# TODO update the JSON string below
json = "{}"
# create an instance of AccountSpecifics from a JSON string
account_specifics_instance = AccountSpecifics.from_json(json)
# print the JSON string representation of the object
print(AccountSpecifics.to_json())

# convert the object into a dict
account_specifics_dict = account_specifics_instance.to_dict()
# create an instance of AccountSpecifics from a dict
account_specifics_from_dict = AccountSpecifics.from_dict(account_specifics_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


