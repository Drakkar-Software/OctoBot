# DslKeyword

Definition of one DSL keyword (signature and configuration).

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Stable DSL keyword id. | 
**category** | [**DslKeywordCategory**](DslKeywordCategory.md) |  | 
**label** | **str** |  | 
**description** | **str** |  | 
**inputs** | [**List[DslParameter]**](DslParameter.md) |  | 
**outputs** | [**List[DslParameter]**](DslParameter.md) |  | 

## Example

```python
from octobot_protocol.models.dsl_keyword import DslKeyword

# TODO update the JSON string below
json = "{}"
# create an instance of DslKeyword from a JSON string
dsl_keyword_instance = DslKeyword.from_json(json)
# print the JSON string representation of the object
print(DslKeyword.to_json())

# convert the object into a dict
dsl_keyword_dict = dsl_keyword_instance.to_dict()
# create an instance of DslKeyword from a dict
dsl_keyword_from_dict = DslKeyword.from_dict(dsl_keyword_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


