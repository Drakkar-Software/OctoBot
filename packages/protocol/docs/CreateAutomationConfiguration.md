# CreateAutomationConfiguration

CreateAutomationConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**UserActionType**](UserActionType.md) | automation_create | 
**configuration** | [**AutomationConfiguration**](AutomationConfiguration.md) |  | 

## Example

```python
from octobot_protocol.models.create_automation_configuration import CreateAutomationConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of CreateAutomationConfiguration from a JSON string
create_automation_configuration_instance = CreateAutomationConfiguration.from_json(json)
# print the JSON string representation of the object
print(CreateAutomationConfiguration.to_json())

# convert the object into a dict
create_automation_configuration_dict = create_automation_configuration_instance.to_dict()
# create an instance of CreateAutomationConfiguration from a dict
create_automation_configuration_from_dict = CreateAutomationConfiguration.from_dict(create_automation_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


