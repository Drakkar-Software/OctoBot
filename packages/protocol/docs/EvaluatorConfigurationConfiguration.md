# EvaluatorConfigurationConfiguration


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**EvaluatorType**](EvaluatorType.md) | EMAMomentumEvaluator | 
**period_length** | **float** |  | 
**short_threshold** | **float** |  | 
**long_threshold** | **float** |  | 
**trend_change_identifier** | **bool** |  | [optional] [default to False]
**price_threshold_percent** | **float** |  | 
**reverse_signal** | **bool** | When true, emits a short signal when the current price is bellow the EMA. | [default to False]

## Example

```python
from octobot_protocol.models.evaluator_configuration_configuration import EvaluatorConfigurationConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluatorConfigurationConfiguration from a JSON string
evaluator_configuration_configuration_instance = EvaluatorConfigurationConfiguration.from_json(json)
# print the JSON string representation of the object
print(EvaluatorConfigurationConfiguration.to_json())

# convert the object into a dict
evaluator_configuration_configuration_dict = evaluator_configuration_configuration_instance.to_dict()
# create an instance of EvaluatorConfigurationConfiguration from a dict
evaluator_configuration_configuration_from_dict = EvaluatorConfigurationConfiguration.from_dict(evaluator_configuration_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


