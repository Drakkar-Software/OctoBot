# EditExchangeConfigConfiguration

EditExchangeConfigConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**UserActionType**](UserActionType.md) | exchange_config_edit | 
**id** | **str** |  | 
**configuration** | [**ExchangeConfig**](ExchangeConfig.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.edit_exchange_config_configuration import EditExchangeConfigConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of EditExchangeConfigConfiguration from a JSON string
edit_exchange_config_configuration_instance = EditExchangeConfigConfiguration.from_json(json)
# print the JSON string representation of the object
print(EditExchangeConfigConfiguration.to_json())

# convert the object into a dict
edit_exchange_config_configuration_dict = edit_exchange_config_configuration_instance.to_dict()
# create an instance of EditExchangeConfigConfiguration from a dict
edit_exchange_config_configuration_from_dict = EditExchangeConfigConfiguration.from_dict(edit_exchange_config_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


