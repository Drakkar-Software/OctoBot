# CreateExchangeConfigConfiguration

CreateExchangeConfigConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**UserActionType**](UserActionType.md) | exchange_config_create | 
**configuration** | [**ExchangeConfig**](ExchangeConfig.md) |  | 

## Example

```python
from octobot_protocol.models.create_exchange_config_configuration import CreateExchangeConfigConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of CreateExchangeConfigConfiguration from a JSON string
create_exchange_config_configuration_instance = CreateExchangeConfigConfiguration.from_json(json)
# print the JSON string representation of the object
print(CreateExchangeConfigConfiguration.to_json())

# convert the object into a dict
create_exchange_config_configuration_dict = create_exchange_config_configuration_instance.to_dict()
# create an instance of CreateExchangeConfigConfiguration from a dict
create_exchange_config_configuration_from_dict = CreateExchangeConfigConfiguration.from_dict(create_exchange_config_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


