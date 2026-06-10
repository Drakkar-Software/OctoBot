# StrategyEvaluatorConfigurationConfiguration


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**StrategyEvaluatorType**](StrategyEvaluatorType.md) | TechnicalAnalysisStrategyEvaluator | 
**time_frames_to_weight** | [**List[TimeFrameAndWeight]**](TimeFrameAndWeight.md) |  | 

## Example

```python
from octobot_protocol.models.strategy_evaluator_configuration_configuration import StrategyEvaluatorConfigurationConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of StrategyEvaluatorConfigurationConfiguration from a JSON string
strategy_evaluator_configuration_configuration_instance = StrategyEvaluatorConfigurationConfiguration.from_json(json)
# print the JSON string representation of the object
print(StrategyEvaluatorConfigurationConfiguration.to_json())

# convert the object into a dict
strategy_evaluator_configuration_configuration_dict = strategy_evaluator_configuration_configuration_instance.to_dict()
# create an instance of StrategyEvaluatorConfigurationConfiguration from a dict
strategy_evaluator_configuration_configuration_from_dict = StrategyEvaluatorConfigurationConfiguration.from_dict(strategy_evaluator_configuration_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


