# BlockchainAccount

BlockchainAccount

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**blockchain** | **str** |  | 
**network** | **str** |  | [optional] 
**public_key** | **str** |  | [optional] 
**private_key** | **str** |  | [optional] 
**passphrase** | **str** |  | [optional] 

## Example

```python
from octobot_protocol.models.blockchain_account import BlockchainAccount

# TODO update the JSON string below
json = "{}"
# create an instance of BlockchainAccount from a JSON string
blockchain_account_instance = BlockchainAccount.from_json(json)
# print the JSON string representation of the object
print(BlockchainAccount.to_json())

# convert the object into a dict
blockchain_account_dict = blockchain_account_instance.to_dict()
# create an instance of BlockchainAccount from a dict
blockchain_account_from_dict = BlockchainAccount.from_dict(blockchain_account_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


