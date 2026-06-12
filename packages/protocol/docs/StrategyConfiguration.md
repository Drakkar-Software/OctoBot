# StrategyConfiguration


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**ActionConfigurationType**](ActionConfigurationType.md) | generic_workflow | 
**pair_settings** | [**List[MarketMakingSymbolConfiguration]**](MarketMakingSymbolConfiguration.md) |  | 
**name** | **str** | Trading mode tentacle class name, e.g. DCATradingMode, GridTradingMode | 
**config** | **Dict[str, object]** |  | 
**symbols** | **List[str]** |  | [optional] 
**strategies** | [**List[StrategyEvaluatorConfiguration]**](StrategyEvaluatorConfiguration.md) |  | [optional] 
**evaluators** | [**List[EvaluatorConfiguration]**](EvaluatorConfiguration.md) |  | [optional] 
**strategy_id** | **str** |  | 
**profile_data** | **object** |  | 
**actions** | [**List[Action]**](Action.md) |  | 

## Example

```python
from octobot_protocol.models.strategy_configuration import StrategyConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of StrategyConfiguration from a JSON string
strategy_configuration_instance = StrategyConfiguration.from_json(json)
# print the JSON string representation of the object
print(StrategyConfiguration.to_json())

# convert the object into a dict
strategy_configuration_dict = strategy_configuration_instance.to_dict()
# create an instance of StrategyConfiguration from a dict
strategy_configuration_from_dict = StrategyConfiguration.from_dict(strategy_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


