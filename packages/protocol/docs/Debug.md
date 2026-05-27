# Debug

Debug view of all automations and user actions

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**automations** | [**List[AutomationState]**](AutomationState.md) |  | 
**user_actions** | [**List[UserAction]**](UserAction.md) |  | 
**accounts** | [**List[Account]**](Account.md) |  | [optional] 
**exchange_configs** | [**List[ExchangeConfig]**](ExchangeConfig.md) |  | [optional] 
**account_tradings** | [**List[AccountTradingWithAccountId]**](AccountTradingWithAccountId.md) |  | [optional] 
**local_strategies** | [**List[Strategy]**](Strategy.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.debug import Debug

# TODO update the JSON string below
json = "{}"
# create an instance of Debug from a JSON string
debug_instance = Debug.from_json(json)
# print the JSON string representation of the object
print(Debug.to_json())

# convert the object into a dict
debug_dict = debug_instance.to_dict()
# create an instance of Debug from a dict
debug_from_dict = Debug.from_dict(debug_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


