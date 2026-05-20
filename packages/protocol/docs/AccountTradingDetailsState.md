# AccountTradingDetailsState

AccountsTradingDetailsState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**details** | [**List[AccountTradingDetails]**](AccountTradingDetails.md) |  | 

## Example

```python
from octobot_protocol.models.account_trading_details_state import AccountTradingDetailsState

# TODO update the JSON string below
json = "{}"
# create an instance of AccountTradingDetailsState from a JSON string
account_trading_details_state_instance = AccountTradingDetailsState.from_json(json)
# print the JSON string representation of the object
print(AccountTradingDetailsState.to_json())

# convert the object into a dict
account_trading_details_state_dict = account_trading_details_state_instance.to_dict()
# create an instance of AccountTradingDetailsState from a dict
account_trading_details_state_from_dict = AccountTradingDetailsState.from_dict(account_trading_details_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


