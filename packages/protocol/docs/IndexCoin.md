# IndexCoin

IndexCoin

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**ratio** | **float** |  | [default to 1]

## Example

```python
from octobot_protocol.models.index_coin import IndexCoin

# TODO update the JSON string below
json = "{}"
# create an instance of IndexCoin from a JSON string
index_coin_instance = IndexCoin.from_json(json)
# print the JSON string representation of the object
print(IndexCoin.to_json())

# convert the object into a dict
index_coin_dict = index_coin_instance.to_dict()
# create an instance of IndexCoin from a dict
index_coin_from_dict = IndexCoin.from_dict(index_coin_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


