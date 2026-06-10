# SimpleStrategyEvaluatorConfiguration

SimpleStrategyEvaluatorConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**StrategyEvaluatorType**](StrategyEvaluatorType.md) | SimpleStrategyEvaluator | 

## Example

```python
from octobot_protocol.models.simple_strategy_evaluator_configuration import SimpleStrategyEvaluatorConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of SimpleStrategyEvaluatorConfiguration from a JSON string
simple_strategy_evaluator_configuration_instance = SimpleStrategyEvaluatorConfiguration.from_json(json)
# print the JSON string representation of the object
print(SimpleStrategyEvaluatorConfiguration.to_json())

# convert the object into a dict
simple_strategy_evaluator_configuration_dict = simple_strategy_evaluator_configuration_instance.to_dict()
# create an instance of SimpleStrategyEvaluatorConfiguration from a dict
simple_strategy_evaluator_configuration_from_dict = SimpleStrategyEvaluatorConfiguration.from_dict(simple_strategy_evaluator_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


