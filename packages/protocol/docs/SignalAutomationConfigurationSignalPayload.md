# SignalAutomationConfigurationSignalPayload

Optional payload associated with signal_type. Schema stays generic; see description for wire shapes. When signal_type is actions: a single action object, an array of action objects, or an object with an actions array. Each action object may use signal (param=val string, JSON signal string, or value resolved to DSL), a bare signal dict containing the flow signal key (e.g. SIGNAL), or dsl_script with id for direct DSL passthrough without resolution. Optional fields: id (default generated when using signal), await_execution_result (default true). signal is resolved to DSL; dsl_script is executed as-is. When signal_type is trading_signal: a trading-signal dict or one-element array. forced_trigger ignores payload.

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


