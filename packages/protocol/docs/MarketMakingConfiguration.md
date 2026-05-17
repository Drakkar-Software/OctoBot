# MarketMakingConfiguration

Per-symbol market making parameters.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**ActionConfigurationType**](ActionConfigurationType.md) | market_making | 
**pair_settings** | [**List[MarketMakingSymbolConfiguration]**](MarketMakingSymbolConfiguration.md) |  | 

## Example

```python
from octobot_protocol.models.market_making_configuration import MarketMakingConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of MarketMakingConfiguration from a JSON string
market_making_configuration_instance = MarketMakingConfiguration.from_json(json)
# print the JSON string representation of the object
print(MarketMakingConfiguration.to_json())

# convert the object into a dict
market_making_configuration_dict = market_making_configuration_instance.to_dict()
# create an instance of MarketMakingConfiguration from a dict
market_making_configuration_from_dict = MarketMakingConfiguration.from_dict(market_making_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


