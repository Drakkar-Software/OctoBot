# StrategiesState

StrategiesState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**strategies** | [**List[Strategy]**](Strategy.md) |  | 

## Example

```python
from octobot_protocol.models.strategies_state import StrategiesState

# TODO update the JSON string below
json = "{}"
# create an instance of StrategiesState from a JSON string
strategies_state_instance = StrategiesState.from_json(json)
# print the JSON string representation of the object
print(StrategiesState.to_json())

# convert the object into a dict
strategies_state_dict = strategies_state_instance.to_dict()
# create an instance of StrategiesState from a dict
strategies_state_from_dict = StrategiesState.from_dict(strategies_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


