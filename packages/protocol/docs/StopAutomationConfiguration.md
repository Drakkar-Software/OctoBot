# StopAutomationConfiguration

StopAutomationConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**action_type** | [**ActionType**](ActionType.md) |  | 

## Example

```python
from octobot_protocol.models.stop_automation_configuration import StopAutomationConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of StopAutomationConfiguration from a JSON string
stop_automation_configuration_instance = StopAutomationConfiguration.from_json(json)
# print the JSON string representation of the object
print(StopAutomationConfiguration.to_json())

# convert the object into a dict
stop_automation_configuration_dict = stop_automation_configuration_instance.to_dict()
# create an instance of StopAutomationConfiguration from a dict
stop_automation_configuration_from_dict = StopAutomationConfiguration.from_dict(stop_automation_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


