# SignalBotConfiguration

SignalBotConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**ActionConfigurationType**](ActionConfigurationType.md) | signal_bot | 
**sync_interval_with_open_trades_seconds** | **float** | Periodic tick interval when the automation has open trades (open orders and/or open positions). | 
**sync_interval_without_open_trades_seconds** | **float** | Periodic tick interval when the automation is idle (no open trades). | 

## Example

```python
from octobot_protocol.models.signal_bot_configuration import SignalBotConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of SignalBotConfiguration from a JSON string
signal_bot_configuration_instance = SignalBotConfiguration.from_json(json)
# print the JSON string representation of the object
print(SignalBotConfiguration.to_json())

# convert the object into a dict
signal_bot_configuration_dict = signal_bot_configuration_instance.to_dict()
# create an instance of SignalBotConfiguration from a dict
signal_bot_configuration_from_dict = SignalBotConfiguration.from_dict(signal_bot_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


