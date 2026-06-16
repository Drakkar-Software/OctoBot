# AutomationConfiguration

AutomationConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | [optional] 
**name** | **str** |  | 
**description** | **str** |  | [optional] 
**created_at** | **datetime** |  | 
**updated_at** | **datetime** |  | [optional] 
**strategy** | [**StrategyReference**](StrategyReference.md) |  | 
**accounts** | [**List[AccountReference]**](AccountReference.md) |  | 

## Example

```python
from octobot_protocol.models.automation_configuration import AutomationConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of AutomationConfiguration from a JSON string
automation_configuration_instance = AutomationConfiguration.from_json(json)
# print the JSON string representation of the object
print(AutomationConfiguration.to_json())

# convert the object into a dict
automation_configuration_dict = automation_configuration_instance.to_dict()
# create an instance of AutomationConfiguration from a dict
automation_configuration_from_dict = AutomationConfiguration.from_dict(automation_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


