# UpdateHistoricalExchangesDataConfiguration

UpdateHistoricalExchangesDataConfiguration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action_type** | [**UserActionType**](UserActionType.md) | update_historical_exchanges_data | 
**account_ids** | **List[str]** |  | [optional] 

## Example

```python
from octobot_protocol.models.update_historical_exchanges_data_configuration import UpdateHistoricalExchangesDataConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of UpdateHistoricalExchangesDataConfiguration from a JSON string
update_historical_exchanges_data_configuration_instance = UpdateHistoricalExchangesDataConfiguration.from_json(json)
# print the JSON string representation of the object
print(UpdateHistoricalExchangesDataConfiguration.to_json())

# convert the object into a dict
update_historical_exchanges_data_configuration_dict = update_historical_exchanges_data_configuration_instance.to_dict()
# create an instance of UpdateHistoricalExchangesDataConfiguration from a dict
update_historical_exchanges_data_configuration_from_dict = UpdateHistoricalExchangesDataConfiguration.from_dict(update_historical_exchanges_data_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


