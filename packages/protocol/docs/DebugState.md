# DebugState

DebugState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**debug** | [**Debug**](Debug.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.debug_state import DebugState

# TODO update the JSON string below
json = "{}"
# create an instance of DebugState from a JSON string
debug_state_instance = DebugState.from_json(json)
# print the JSON string representation of the object
print(DebugState.to_json())

# convert the object into a dict
debug_state_dict = debug_state_instance.to_dict()
# create an instance of DebugState from a dict
debug_state_from_dict = DebugState.from_dict(debug_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


