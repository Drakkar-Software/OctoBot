# AccountDetails


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
from octobot_protocol.models.account_details import AccountDetails

# TODO update the JSON string below
json = "{}"
# create an instance of AccountDetails from a JSON string
account_details_instance = AccountDetails.from_json(json)
# print the JSON string representation of the object
print(AccountDetails.to_json())

# convert the object into a dict
account_details_dict = account_details_instance.to_dict()
# create an instance of AccountDetails from a dict
account_details_from_dict = AccountDetails.from_dict(account_details_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


