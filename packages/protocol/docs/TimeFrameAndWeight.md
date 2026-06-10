# TimeFrameAndWeight

TimeFrameAndWeight

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**time_frame** | [**TimeFrame**](TimeFrame.md) |  | 
**weight** | **float** |  | 

## Example

```python
from octobot_protocol.models.time_frame_and_weight import TimeFrameAndWeight

# TODO update the JSON string below
json = "{}"
# create an instance of TimeFrameAndWeight from a JSON string
time_frame_and_weight_instance = TimeFrameAndWeight.from_json(json)
# print the JSON string representation of the object
print(TimeFrameAndWeight.to_json())

# convert the object into a dict
time_frame_and_weight_dict = time_frame_and_weight_instance.to_dict()
# create an instance of TimeFrameAndWeight from a dict
time_frame_and_weight_from_dict = TimeFrameAndWeight.from_dict(time_frame_and_weight_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


