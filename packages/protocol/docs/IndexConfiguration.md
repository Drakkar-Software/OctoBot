# IndexConfiguration

IndexConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | **str** |  | 
**coins** | [**List[IndexCoin]**](IndexCoin.md) |  | 
**rebalance_trigger_min_percent** | **float** |  | 

## Example

```python
from octobot_protocol.models.index_configuration import IndexConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of IndexConfiguration from a JSON string
index_configuration_instance = IndexConfiguration.from_json(json)
# print the JSON string representation of the object
print(IndexConfiguration.to_json())

# convert the object into a dict
index_configuration_dict = index_configuration_instance.to_dict()
# create an instance of IndexConfiguration from a dict
index_configuration_from_dict = IndexConfiguration.from_dict(index_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


