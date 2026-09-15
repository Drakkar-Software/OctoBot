# NodeEndpoint

A paired node's address triple. Deliberately structural: any host/port/secure works. Not a caller's own document type for a list of paired nodes.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**host** | **str** |  | 
**port** | **int** |  | 
**secure** | **bool** |  | [optional] 

## Example

```python
from octobot_protocol.models.node_endpoint import NodeEndpoint

# TODO update the JSON string below
json = "{}"
# create an instance of NodeEndpoint from a JSON string
node_endpoint_instance = NodeEndpoint.from_json(json)
# print the JSON string representation of the object
print(NodeEndpoint.to_json())

# convert the object into a dict
node_endpoint_dict = node_endpoint_instance.to_dict()
# create an instance of NodeEndpoint from a dict
node_endpoint_from_dict = NodeEndpoint.from_dict(node_endpoint_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


