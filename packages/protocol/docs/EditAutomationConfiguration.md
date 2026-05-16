# EditAutomationConfiguration

EditAutomationConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**action_type** | **str** |  | 
**configuration** | [**AutomationConfiguration**](AutomationConfiguration.md) |  | 

## Example

```python
from octobot_protocol.models.edit_automation_configuration import EditAutomationConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of EditAutomationConfiguration from a JSON string
edit_automation_configuration_instance = EditAutomationConfiguration.from_json(json)
# print the JSON string representation of the object
print(EditAutomationConfiguration.to_json())

# convert the object into a dict
edit_automation_configuration_dict = edit_automation_configuration_instance.to_dict()
# create an instance of EditAutomationConfiguration from a dict
edit_automation_configuration_from_dict = EditAutomationConfiguration.from_dict(edit_automation_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


