# StrategyEvaluatorConfiguration

StrategyEvaluatorConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**time_frames** | [**List[TimeFrame]**](TimeFrame.md) |  | 
**configuration** | [**StrategyEvaluatorConfigurationConfiguration**](StrategyEvaluatorConfigurationConfiguration.md) |  | 

## Example

```python
from octobot_protocol.models.strategy_evaluator_configuration import StrategyEvaluatorConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of StrategyEvaluatorConfiguration from a JSON string
strategy_evaluator_configuration_instance = StrategyEvaluatorConfiguration.from_json(json)
# print the JSON string representation of the object
print(StrategyEvaluatorConfiguration.to_json())

# convert the object into a dict
strategy_evaluator_configuration_dict = strategy_evaluator_configuration_instance.to_dict()
# create an instance of StrategyEvaluatorConfiguration from a dict
strategy_evaluator_configuration_from_dict = StrategyEvaluatorConfiguration.from_dict(strategy_evaluator_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


