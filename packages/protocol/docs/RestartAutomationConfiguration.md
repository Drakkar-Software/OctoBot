# RestartAutomationConfiguration

RestartAutomationConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**action_type** | [**UserActionType**](UserActionType.md) | automation_restart | 

## Example

```python
from octobot_protocol.models.restart_automation_configuration import RestartAutomationConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of RestartAutomationConfiguration from a JSON string
restart_automation_configuration_instance = RestartAutomationConfiguration.from_json(json)
# print the JSON string representation of the object
print(RestartAutomationConfiguration.to_json())

# convert the object into a dict
restart_automation_configuration_dict = restart_automation_configuration_instance.to_dict()
# create an instance of RestartAutomationConfiguration from a dict
restart_automation_configuration_from_dict = RestartAutomationConfiguration.from_dict(restart_automation_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


