# PositionSummary

PositionSummary

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**symbol** | **str** |  | 

## Example

```python
from octobot_protocol.models.position_summary import PositionSummary

# TODO update the JSON string below
json = "{}"
# create an instance of PositionSummary from a JSON string
position_summary_instance = PositionSummary.from_json(json)
# print the JSON string representation of the object
print(PositionSummary.to_json())

# convert the object into a dict
position_summary_dict = position_summary_instance.to_dict()
# create an instance of PositionSummary from a dict
position_summary_from_dict = PositionSummary.from_dict(position_summary_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


