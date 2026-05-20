# PortfolioHistoricalValues

PortfolioHistoricalValues

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**unit** | **str** |  | 
**values** | [**List[PortfolioHistoricalValue]**](PortfolioHistoricalValue.md) |  | 

## Example

```python
from octobot_protocol.models.portfolio_historical_values import PortfolioHistoricalValues

# TODO update the JSON string below
json = "{}"
# create an instance of PortfolioHistoricalValues from a JSON string
portfolio_historical_values_instance = PortfolioHistoricalValues.from_json(json)
# print the JSON string representation of the object
print(PortfolioHistoricalValues.to_json())

# convert the object into a dict
portfolio_historical_values_dict = portfolio_historical_values_instance.to_dict()
# create an instance of PortfolioHistoricalValues from a dict
portfolio_historical_values_from_dict = PortfolioHistoricalValues.from_dict(portfolio_historical_values_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


