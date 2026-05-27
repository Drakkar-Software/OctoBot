# DeleteExchangeConfigConfiguration

DeleteExchangeConfigConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**UserActionType**](UserActionType.md) | exchange_config_delete | 
**id** | **str** |  | 

## Example

```python
from octobot_protocol.models.delete_exchange_config_configuration import DeleteExchangeConfigConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of DeleteExchangeConfigConfiguration from a JSON string
delete_exchange_config_configuration_instance = DeleteExchangeConfigConfiguration.from_json(json)
# print the JSON string representation of the object
print(DeleteExchangeConfigConfiguration.to_json())

# convert the object into a dict
delete_exchange_config_configuration_dict = delete_exchange_config_configuration_instance.to_dict()
# create an instance of DeleteExchangeConfigConfiguration from a dict
delete_exchange_config_configuration_from_dict = DeleteExchangeConfigConfiguration.from_dict(delete_exchange_config_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


