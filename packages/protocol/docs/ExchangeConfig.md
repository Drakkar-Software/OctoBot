# ExchangeConfig

ExchangeConfig

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**name** | **str** |  | 
**exchange** | **str** |  | 
**sandboxed** | **bool** |  | [default to False]
**url** | **str** |  | [optional] 
**dex_config** | [**DEXConfig**](DEXConfig.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.exchange_config import ExchangeConfig

# TODO update the JSON string below
json = "{}"
# create an instance of ExchangeConfig from a JSON string
exchange_config_instance = ExchangeConfig.from_json(json)
# print the JSON string representation of the object
print(ExchangeConfig.to_json())

# convert the object into a dict
exchange_config_dict = exchange_config_instance.to_dict()
# create an instance of ExchangeConfig from a dict
exchange_config_from_dict = ExchangeConfig.from_dict(exchange_config_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


