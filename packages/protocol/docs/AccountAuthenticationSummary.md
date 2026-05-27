# AccountAuthenticationSummary

AccountAuthenticationSummary

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**updated_at** | **datetime** |  | [optional] 
**api_key** | **str** |  | [optional] 
**public_key** | **str** |  | [optional] 

## Example

```python
from octobot_protocol.models.account_authentication_summary import AccountAuthenticationSummary

# TODO update the JSON string below
json = "{}"
# create an instance of AccountAuthenticationSummary from a JSON string
account_authentication_summary_instance = AccountAuthenticationSummary.from_json(json)
# print the JSON string representation of the object
print(AccountAuthenticationSummary.to_json())

# convert the object into a dict
account_authentication_summary_dict = account_authentication_summary_instance.to_dict()
# create an instance of AccountAuthenticationSummary from a dict
account_authentication_summary_from_dict = AccountAuthenticationSummary.from_dict(account_authentication_summary_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


