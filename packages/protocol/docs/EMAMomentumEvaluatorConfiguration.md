# EMAMomentumEvaluatorConfiguration

EMAMomentumEvaluatorConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**EvaluatorType**](EvaluatorType.md) | EMAMomentumEvaluator | 
**period_length** | **float** |  | 
**price_threshold_percent** | **float** |  | 
**reverse_signal** | **bool** |  | [default to False]

## Example

```python
from octobot_protocol.models.ema_momentum_evaluator_configuration import EMAMomentumEvaluatorConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of EMAMomentumEvaluatorConfiguration from a JSON string
ema_momentum_evaluator_configuration_instance = EMAMomentumEvaluatorConfiguration.from_json(json)
# print the JSON string representation of the object
print(EMAMomentumEvaluatorConfiguration.to_json())

# convert the object into a dict
ema_momentum_evaluator_configuration_dict = ema_momentum_evaluator_configuration_instance.to_dict()
# create an instance of EMAMomentumEvaluatorConfiguration from a dict
ema_momentum_evaluator_configuration_from_dict = EMAMomentumEvaluatorConfiguration.from_dict(ema_momentum_evaluator_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


