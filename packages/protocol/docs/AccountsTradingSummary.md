# AccountsTradingSummary

AccountsTradingSummary

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**account_id** | **str** |  | 
**orders** | [**List[Order]**](Order.md) |  | [optional] 
**positions** | [**List[Position]**](Position.md) |  | [optional] 
**trades** | [**List[Trade]**](Trade.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.accounts_trading_summary import AccountsTradingSummary

# TODO update the JSON string below
json = "{}"
# create an instance of AccountsTradingSummary from a JSON string
accounts_trading_summary_instance = AccountsTradingSummary.from_json(json)
# print the JSON string representation of the object
print(AccountsTradingSummary.to_json())

# convert the object into a dict
accounts_trading_summary_dict = accounts_trading_summary_instance.to_dict()
# create an instance of AccountsTradingSummary from a dict
accounts_trading_summary_from_dict = AccountsTradingSummary.from_dict(accounts_trading_summary_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


