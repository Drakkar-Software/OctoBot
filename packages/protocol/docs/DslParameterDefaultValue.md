# DslParameterDefaultValue

Must match parameter_type; for select/time_frame must be one of options[].value.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------

## Example

```python
from octobot_protocol.models.dsl_parameter_default_value import DslParameterDefaultValue

# TODO update the JSON string below
json = "{}"
# create an instance of DslParameterDefaultValue from a JSON string
dsl_parameter_default_value_instance = DslParameterDefaultValue.from_json(json)
# print the JSON string representation of the object
print(DslParameterDefaultValue.to_json())

# convert the object into a dict
dsl_parameter_default_value_dict = dsl_parameter_default_value_instance.to_dict()
# create an instance of DslParameterDefaultValue from a dict
dsl_parameter_default_value_from_dict = DslParameterDefaultValue.from_dict(dsl_parameter_default_value_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


