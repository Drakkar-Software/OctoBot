# DslParameterOption

Selectable value for a DSL parameter.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **str** |  | 
**label** | **str** |  | 

## Example

```python
from octobot_protocol.models.dsl_parameter_option import DslParameterOption

# TODO update the JSON string below
json = "{}"
# create an instance of DslParameterOption from a JSON string
dsl_parameter_option_instance = DslParameterOption.from_json(json)
# print the JSON string representation of the object
print(DslParameterOption.to_json())

# convert the object into a dict
dsl_parameter_option_dict = dsl_parameter_option_instance.to_dict()
# create an instance of DslParameterOption from a dict
dsl_parameter_option_from_dict = DslParameterOption.from_dict(dsl_parameter_option_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


