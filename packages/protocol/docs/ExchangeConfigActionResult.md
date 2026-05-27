# ExchangeConfigActionResult

ExchangeConfigActionResult

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**updated_at** | **datetime** |  | 
**error_message** | [**ExchangeConfigActionResultErrorMessage**](ExchangeConfigActionResultErrorMessage.md) |  | [optional] 
**error_details** | **str** |  | [optional] 
**result_type** | [**UserActionResultType**](UserActionResultType.md) |  | 

## Example

```python
from octobot_protocol.models.exchange_config_action_result import ExchangeConfigActionResult

# TODO update the JSON string below
json = "{}"
# create an instance of ExchangeConfigActionResult from a JSON string
exchange_config_action_result_instance = ExchangeConfigActionResult.from_json(json)
# print the JSON string representation of the object
print(ExchangeConfigActionResult.to_json())

# convert the object into a dict
exchange_config_action_result_dict = exchange_config_action_result_instance.to_dict()
# create an instance of ExchangeConfigActionResult from a dict
exchange_config_action_result_from_dict = ExchangeConfigActionResult.from_dict(exchange_config_action_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


