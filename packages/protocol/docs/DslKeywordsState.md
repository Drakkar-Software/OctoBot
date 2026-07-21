# DslKeywordsState

Versioned list of DSL keywords available on a node.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**keywords** | [**List[DslKeyword]**](DslKeyword.md) | Available keywords in intended display order. | 

## Example

```python
from octobot_protocol.models.dsl_keywords_state import DslKeywordsState

# TODO update the JSON string below
json = "{}"
# create an instance of DslKeywordsState from a JSON string
dsl_keywords_state_instance = DslKeywordsState.from_json(json)
# print the JSON string representation of the object
print(DslKeywordsState.to_json())

# convert the object into a dict
dsl_keywords_state_dict = dsl_keywords_state_instance.to_dict()
# create an instance of DslKeywordsState from a dict
dsl_keywords_state_from_dict = DslKeywordsState.from_dict(dsl_keywords_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


