# RSIMomentumEvaluatorConfiguration

RSIMomentumEvaluatorConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**EvaluatorType**](EvaluatorType.md) | RSIMomentumEvaluator | 
**period_length** | **float** |  | 
**short_threshold** | **float** |  | 
**long_threshold** | **float** |  | 

## Example

```python
from octobot_protocol.models.rsi_momentum_evaluator_configuration import RSIMomentumEvaluatorConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of RSIMomentumEvaluatorConfiguration from a JSON string
rsi_momentum_evaluator_configuration_instance = RSIMomentumEvaluatorConfiguration.from_json(json)
# print the JSON string representation of the object
print(RSIMomentumEvaluatorConfiguration.to_json())

# convert the object into a dict
rsi_momentum_evaluator_configuration_dict = rsi_momentum_evaluator_configuration_instance.to_dict()
# create an instance of RSIMomentumEvaluatorConfiguration from a dict
rsi_momentum_evaluator_configuration_from_dict = RSIMomentumEvaluatorConfiguration.from_dict(rsi_momentum_evaluator_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


