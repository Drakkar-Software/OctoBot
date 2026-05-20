# CancelPolicy

CancelPolicy

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | [**CancelPolicyType**](CancelPolicyType.md) |  | 
**specifics** | **object** |  | [optional] 

## Example

```python
from octobot_protocol.models.cancel_policy import CancelPolicy

# TODO update the JSON string below
json = "{}"
# create an instance of CancelPolicy from a JSON string
cancel_policy_instance = CancelPolicy.from_json(json)
# print the JSON string representation of the object
print(CancelPolicy.to_json())

# convert the object into a dict
cancel_policy_dict = cancel_policy_instance.to_dict()
# create an instance of CancelPolicy from a dict
cancel_policy_from_dict = CancelPolicy.from_dict(cancel_policy_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


