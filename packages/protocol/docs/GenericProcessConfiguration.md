# GenericProcessConfiguration

GenericProcessConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**ActionConfigurationType**](ActionConfigurationType.md) | generic_process | 
**profile_data** | **object** |  | 

## Example

```python
from octobot_protocol.models.generic_process_configuration import GenericProcessConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of GenericProcessConfiguration from a JSON string
generic_process_configuration_instance = GenericProcessConfiguration.from_json(json)
# print the JSON string representation of the object
print(GenericProcessConfiguration.to_json())

# convert the object into a dict
generic_process_configuration_dict = generic_process_configuration_instance.to_dict()
# create an instance of GenericProcessConfiguration from a dict
generic_process_configuration_from_dict = GenericProcessConfiguration.from_dict(generic_process_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


