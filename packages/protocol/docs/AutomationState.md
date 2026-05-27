# AutomationState

AutomationState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**status** | [**TaskStatus**](TaskStatus.md) |  | 
**error** | **str** |  | [optional] 
**error_message** | **str** |  | [optional] 
**metadata** | [**AutomationMetadata**](AutomationMetadata.md) |  | 
**actions** | [**List[Action]**](Action.md) |  | [optional] 
**priority_actions** | [**List[Action]**](Action.md) |  | [optional] 
**exchanges** | **List[str]** |  | [optional] 
**exchange_account_ids** | **List[str]** |  | [optional] 
**assets** | [**List[DetailedAssetsForTradingType]**](DetailedAssetsForTradingType.md) |  | [optional] 
**orders** | [**List[OrderSummary]**](OrderSummary.md) |  | [optional] 
**trades** | [**List[TradeSummary]**](TradeSummary.md) |  | [optional] 
**positions** | [**List[PositionSummary]**](PositionSummary.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.automation_state import AutomationState

# TODO update the JSON string below
json = "{}"
# create an instance of AutomationState from a JSON string
automation_state_instance = AutomationState.from_json(json)
# print the JSON string representation of the object
print(AutomationState.to_json())

# convert the object into a dict
automation_state_dict = automation_state_instance.to_dict()
# create an instance of AutomationState from a dict
automation_state_from_dict = AutomationState.from_dict(automation_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


