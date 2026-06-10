# EvaluatorConfiguration

EvaluatorConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**symbols** | **List[str]** |  | 
**include_in_construction_candle** | **bool** |  | [optional] [default to False]
**configuration** | [**EvaluatorConfigurationConfiguration**](EvaluatorConfigurationConfiguration.md) |  | 

## Example

```python
from octobot_protocol.models.evaluator_configuration import EvaluatorConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluatorConfiguration from a JSON string
evaluator_configuration_instance = EvaluatorConfiguration.from_json(json)
# print the JSON string representation of the object
print(EvaluatorConfiguration.to_json())

# convert the object into a dict
evaluator_configuration_dict = evaluator_configuration_instance.to_dict()
# create an instance of EvaluatorConfiguration from a dict
evaluator_configuration_from_dict = EvaluatorConfiguration.from_dict(evaluator_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


