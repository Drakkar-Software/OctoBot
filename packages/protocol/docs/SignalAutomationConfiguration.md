# SignalAutomationConfiguration

SignalAutomationConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**UserActionType**](UserActionType.md) | automation_signal | 
**automation_id** | **str** |  | 
**signal_type** | [**AutomationSignalType**](AutomationSignalType.md) |  | 
**signal_payload** | [**SignalAutomationConfigurationSignalPayload**](SignalAutomationConfigurationSignalPayload.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.signal_automation_configuration import SignalAutomationConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of SignalAutomationConfiguration from a JSON string
signal_automation_configuration_instance = SignalAutomationConfiguration.from_json(json)
# print the JSON string representation of the object
print(SignalAutomationConfiguration.to_json())

# convert the object into a dict
signal_automation_configuration_dict = signal_automation_configuration_instance.to_dict()
# create an instance of SignalAutomationConfiguration from a dict
signal_automation_configuration_from_dict = SignalAutomationConfiguration.from_dict(signal_automation_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


