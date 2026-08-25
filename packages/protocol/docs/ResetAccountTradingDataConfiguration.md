# ResetAccountTradingDataConfiguration

ResetAccountTradingDataConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**UserActionType**](UserActionType.md) | reset_account_trading_data | 
**account_ids** | **List[str]** |  | 

## Example

```python
from octobot_protocol.models.reset_account_trading_data_configuration import ResetAccountTradingDataConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of ResetAccountTradingDataConfiguration from a JSON string
reset_account_trading_data_configuration_instance = ResetAccountTradingDataConfiguration.from_json(json)
# print the JSON string representation of the object
print(ResetAccountTradingDataConfiguration.to_json())

# convert the object into a dict
reset_account_trading_data_configuration_dict = reset_account_trading_data_configuration_instance.to_dict()
# create an instance of ResetAccountTradingDataConfiguration from a dict
reset_account_trading_data_configuration_from_dict = ResetAccountTradingDataConfiguration.from_dict(reset_account_trading_data_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


