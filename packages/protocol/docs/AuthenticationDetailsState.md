# AuthenticationDetailsState

AuthenticationDetailsState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**details** | [**List[AccountAuthenticationDetails]**](AccountAuthenticationDetails.md) |  | 

## Example

```python
from octobot_protocol.models.authentication_details_state import AuthenticationDetailsState

# TODO update the JSON string below
json = "{}"
# create an instance of AuthenticationDetailsState from a JSON string
authentication_details_state_instance = AuthenticationDetailsState.from_json(json)
# print the JSON string representation of the object
print(AuthenticationDetailsState.to_json())

# convert the object into a dict
authentication_details_state_dict = authentication_details_state_instance.to_dict()
# create an instance of AuthenticationDetailsState from a dict
authentication_details_state_from_dict = AuthenticationDetailsState.from_dict(authentication_details_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


