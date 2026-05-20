# PortfolioHistoricalValuesState

PortfolioHistoricalValuesState

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** |  | 
**history** | [**PortfolioHistoricalValues**](PortfolioHistoricalValues.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.portfolio_historical_values_state import PortfolioHistoricalValuesState

# TODO update the JSON string below
json = "{}"
# create an instance of PortfolioHistoricalValuesState from a JSON string
portfolio_historical_values_state_instance = PortfolioHistoricalValuesState.from_json(json)
# print the JSON string representation of the object
print(PortfolioHistoricalValuesState.to_json())

# convert the object into a dict
portfolio_historical_values_state_dict = portfolio_historical_values_state_instance.to_dict()
# create an instance of PortfolioHistoricalValuesState from a dict
portfolio_historical_values_state_from_dict = PortfolioHistoricalValuesState.from_dict(portfolio_historical_values_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


