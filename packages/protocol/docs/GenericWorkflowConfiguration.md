# GenericWorkflowConfiguration

GenericWorkflowConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**ActionConfigurationType**](ActionConfigurationType.md) |  | 
**actions** | [**List[Action]**](Action.md) |  | 

## Example

```python
from octobot_protocol.models.generic_workflow_configuration import GenericWorkflowConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of GenericWorkflowConfiguration from a JSON string
generic_workflow_configuration_instance = GenericWorkflowConfiguration.from_json(json)
# print the JSON string representation of the object
print(GenericWorkflowConfiguration.to_json())

# convert the object into a dict
generic_workflow_configuration_dict = generic_workflow_configuration_instance.to_dict()
# create an instance of GenericWorkflowConfiguration from a dict
generic_workflow_configuration_from_dict = GenericWorkflowConfiguration.from_dict(generic_workflow_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


