# ExchangeAvailability

ExchangeAvailability

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**internal_name** | **str** |  | 
**name** | **str** |  | 
**logo** | **str** |  | [optional] 
**available_trading_types** | [**List[TradingType]**](TradingType.md) |  | 
**support_type** | [**ExchangeSupportStatus**](ExchangeSupportStatus.md) |  | [optional] 
**sandboxable** | **bool** |  | [optional] [default to False]
**broker_enabled** | **bool** |  | [optional] [default to False]
**register_url** | **str** |  | [optional] 
**api_url** | **str** |  | [optional] 

## Example

```python
from octobot_protocol.models.exchange_availability import ExchangeAvailability

# TODO update the JSON string below
json = "{}"
# create an instance of ExchangeAvailability from a JSON string
exchange_availability_instance = ExchangeAvailability.from_json(json)
# print the JSON string representation of the object
print(ExchangeAvailability.to_json())

# convert the object into a dict
exchange_availability_dict = exchange_availability_instance.to_dict()
# create an instance of ExchangeAvailability from a dict
exchange_availability_from_dict = ExchangeAvailability.from_dict(exchange_availability_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


