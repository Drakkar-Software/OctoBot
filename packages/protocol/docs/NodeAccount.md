# NodeAccount

octobot_node.models.Account (distinct name: NodeAccount)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**type** | **str** |  | 
**name** | **str** |  | 
**is_simulated** | **bool** |  | 
**description** | **str** |  | [optional] 
**created_at** | **datetime** |  | 
**updated_at** | **datetime** |  | [optional] 
**exchange_account** | [**ExchangeAccount**](ExchangeAccount.md) |  | [optional] 
**blockchain_account** | [**BlockchainAccount**](BlockchainAccount.md) |  | [optional] 
**generic_account** | [**GenericAccount**](GenericAccount.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.node_account import NodeAccount

# TODO update the JSON string below
json = "{}"
# create an instance of NodeAccount from a JSON string
node_account_instance = NodeAccount.from_json(json)
# print the JSON string representation of the object
print(NodeAccount.to_json())

# convert the object into a dict
node_account_dict = node_account_instance.to_dict()
# create an instance of NodeAccount from a dict
node_account_from_dict = NodeAccount.from_dict(node_account_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


