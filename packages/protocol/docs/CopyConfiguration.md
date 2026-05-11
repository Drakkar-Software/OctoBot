# CopyConfiguration

CopyConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**ActionConfigurationType**](ActionConfigurationType.md) | copy | 
**strategy_id** | **str** |  | 

## Example

```python
from octobot_protocol.models.copy_configuration import CopyConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of CopyConfiguration from a JSON string
copy_configuration_instance = CopyConfiguration.from_json(json)
# print the JSON string representation of the object
print(CopyConfiguration.to_json())

# convert the object into a dict
copy_configuration_dict = copy_configuration_instance.to_dict()
# create an instance of CopyConfiguration from a dict
copy_configuration_from_dict = CopyConfiguration.from_dict(copy_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


