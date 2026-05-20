# AccountTrailingDetailsState

AccountTrailingDetailsState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**account_id** | **str** |  | 
**details** | [**List[AccountTradingDetails]**](AccountTradingDetails.md) |  | 

## Example

```python
from octobot_protocol.models.account_trailing_details_state import AccountTrailingDetailsState

# TODO update the JSON string below
json = "{}"
# create an instance of AccountTrailingDetailsState from a JSON string
account_trailing_details_state_instance = AccountTrailingDetailsState.from_json(json)
# print the JSON string representation of the object
print(AccountTrailingDetailsState.to_json())

# convert the object into a dict
account_trailing_details_state_dict = account_trailing_details_state_instance.to_dict()
# create an instance of AccountTrailingDetailsState from a dict
account_trailing_details_state_from_dict = AccountTrailingDetailsState.from_dict(account_trailing_details_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


