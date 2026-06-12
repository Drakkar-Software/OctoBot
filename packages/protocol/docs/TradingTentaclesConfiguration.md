# TradingTentaclesConfiguration

TradingTentaclesConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**ActionConfigurationType**](ActionConfigurationType.md) | trading_tentacles | 
**name** | **str** | Trading mode tentacle class name, e.g. DCATradingMode, GridTradingMode | 
**config** | **Dict[str, object]** |  | 
**symbols** | **List[str]** |  | [optional] 
**strategies** | [**List[StrategyEvaluatorConfiguration]**](StrategyEvaluatorConfiguration.md) |  | [optional] 
**evaluators** | [**List[EvaluatorConfiguration]**](EvaluatorConfiguration.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.trading_tentacles_configuration import TradingTentaclesConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of TradingTentaclesConfiguration from a JSON string
trading_tentacles_configuration_instance = TradingTentaclesConfiguration.from_json(json)
# print the JSON string representation of the object
print(TradingTentaclesConfiguration.to_json())

# convert the object into a dict
trading_tentacles_configuration_dict = trading_tentacles_configuration_instance.to_dict()
# create an instance of TradingTentaclesConfiguration from a dict
trading_tentacles_configuration_from_dict = TradingTentaclesConfiguration.from_dict(trading_tentacles_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


