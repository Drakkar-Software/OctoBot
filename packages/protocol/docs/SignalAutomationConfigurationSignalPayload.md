# SignalAutomationConfigurationSignalPayload

Optional payload associated with the signal type

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------

## Example

```python
from octobot_protocol.models.signal_automation_configuration_signal_payload import SignalAutomationConfigurationSignalPayload

# TODO update the JSON string below
json = "{}"
# create an instance of SignalAutomationConfigurationSignalPayload from a JSON string
signal_automation_configuration_signal_payload_instance = SignalAutomationConfigurationSignalPayload.from_json(json)
# print the JSON string representation of the object
print(SignalAutomationConfigurationSignalPayload.to_json())

# convert the object into a dict
signal_automation_configuration_signal_payload_dict = signal_automation_configuration_signal_payload_instance.to_dict()
# create an instance of SignalAutomationConfigurationSignalPayload from a dict
signal_automation_configuration_signal_payload_from_dict = SignalAutomationConfigurationSignalPayload.from_dict(signal_automation_configuration_signal_payload_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


