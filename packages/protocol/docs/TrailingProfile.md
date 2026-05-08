# TrailingProfile

TrailingProfile

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | [**TrailingProfileType**](TrailingProfileType.md) |  | 
**details** | **object** |  | [optional] 

## Example

```python
from octobot_protocol.models.trailing_profile import TrailingProfile

# TODO update the JSON string below
json = "{}"
# create an instance of TrailingProfile from a JSON string
trailing_profile_instance = TrailingProfile.from_json(json)
# print the JSON string representation of the object
print(TrailingProfile.to_json())

# convert the object into a dict
trailing_profile_dict = trailing_profile_instance.to_dict()
# create an instance of TrailingProfile from a dict
trailing_profile_from_dict = TrailingProfile.from_dict(trailing_profile_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


