# ChildOctoBotProcessState

ChildOctoBotProcessState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**http_base_url** | **str** |  | 
**web_port** | **int** |  | 
**init_state_ok** | **bool** |  | 

## Example

```python
from octobot_protocol.models.child_octo_bot_process_state import ChildOctoBotProcessState

# TODO update the JSON string below
json = "{}"
# create an instance of ChildOctoBotProcessState from a JSON string
child_octo_bot_process_state_instance = ChildOctoBotProcessState.from_json(json)
# print the JSON string representation of the object
print(ChildOctoBotProcessState.to_json())

# convert the object into a dict
child_octo_bot_process_state_dict = child_octo_bot_process_state_instance.to_dict()
# create an instance of ChildOctoBotProcessState from a dict
child_octo_bot_process_state_from_dict = ChildOctoBotProcessState.from_dict(child_octo_bot_process_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


