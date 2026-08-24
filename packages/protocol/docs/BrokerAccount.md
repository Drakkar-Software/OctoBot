# BrokerAccount

BrokerAccount

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**account_type** | [**AccountType**](AccountType.md) | broker | 
**provider_id** | **str** |  | [optional] 
**exchange_config_ids** | **List[str]** |  | [optional] 

## Example

```python
from octobot_protocol.models.broker_account import BrokerAccount

# TODO update the JSON string below
json = "{}"
# create an instance of BrokerAccount from a JSON string
broker_account_instance = BrokerAccount.from_json(json)
# print the JSON string representation of the object
print(BrokerAccount.to_json())

# convert the object into a dict
broker_account_dict = broker_account_instance.to_dict()
# create an instance of BrokerAccount from a dict
broker_account_from_dict = BrokerAccount.from_dict(broker_account_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


