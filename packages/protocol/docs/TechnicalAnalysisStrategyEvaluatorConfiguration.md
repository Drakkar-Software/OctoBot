# TechnicalAnalysisStrategyEvaluatorConfiguration

TechnicalAnalysisStrategyEvaluatorConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**StrategyEvaluatorType**](StrategyEvaluatorType.md) | TechnicalAnalysisStrategyEvaluator | 
**time_frames_to_weight** | [**List[TimeFrameAndWeight]**](TimeFrameAndWeight.md) |  | 

## Example

```python
from octobot_protocol.models.technical_analysis_strategy_evaluator_configuration import TechnicalAnalysisStrategyEvaluatorConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of TechnicalAnalysisStrategyEvaluatorConfiguration from a JSON string
technical_analysis_strategy_evaluator_configuration_instance = TechnicalAnalysisStrategyEvaluatorConfiguration.from_json(json)
# print the JSON string representation of the object
print(TechnicalAnalysisStrategyEvaluatorConfiguration.to_json())

# convert the object into a dict
technical_analysis_strategy_evaluator_configuration_dict = technical_analysis_strategy_evaluator_configuration_instance.to_dict()
# create an instance of TechnicalAnalysisStrategyEvaluatorConfiguration from a dict
technical_analysis_strategy_evaluator_configuration_from_dict = TechnicalAnalysisStrategyEvaluatorConfiguration.from_dict(technical_analysis_strategy_evaluator_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


