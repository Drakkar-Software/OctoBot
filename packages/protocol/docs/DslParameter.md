# DslParameter

Configurable parameter on a DSL keyword.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Unique within this keyword. | 
**label** | **str** |  | 
**value_type** | [**DslValueType**](DslValueType.md) |  | 
**description** | **str** |  | [optional] 
**default_value** | [**DslParameterDefaultValue**](DslParameterDefaultValue.md) |  | [optional] 
**minimum** | **float** | Only for parameter_type&#x3D;number. | [optional] 
**maximum** | **float** | Only for parameter_type&#x3D;number. | [optional] 
**step** | **float** | Only for parameter_type&#x3D;number. | [optional] 
**options** | [**List[DslParameterOption]**](DslParameterOption.md) | Allowed choices for value_type&#x3D;text or value_type&#x3D;time_frame. | [optional] 
**required** | **bool** |  | [optional] 
**multiple** | **bool** | Accepts more than one value of this parameter. | [optional] 
**primary** | **bool** | Prefer in compact editors. | [optional] 

## Example

```python
from octobot_protocol.models.dsl_parameter import DslParameter

# TODO update the JSON string below
json = "{}"
# create an instance of DslParameter from a JSON string
dsl_parameter_instance = DslParameter.from_json(json)
# print the JSON string representation of the object
print(DslParameter.to_json())

# convert the object into a dict
dsl_parameter_dict = dsl_parameter_instance.to_dict()
# create an instance of DslParameter from a dict
dsl_parameter_from_dict = DslParameter.from_dict(dsl_parameter_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


