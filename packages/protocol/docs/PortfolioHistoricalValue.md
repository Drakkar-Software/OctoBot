# PortfolioHistoricalValue

PortfolioHistoricalValue

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**timestamp** | **datetime** |  | 
**total** | **float** |  | 
**assets** | [**List[HistoricalAssetsForTradingType]**](HistoricalAssetsForTradingType.md) |  | [optional] 

## Example

```python
from octobot_protocol.models.portfolio_historical_value import PortfolioHistoricalValue

# TODO update the JSON string below
json = "{}"
# create an instance of PortfolioHistoricalValue from a JSON string
portfolio_historical_value_instance = PortfolioHistoricalValue.from_json(json)
# print the JSON string representation of the object
print(PortfolioHistoricalValue.to_json())

# convert the object into a dict
portfolio_historical_value_dict = portfolio_historical_value_instance.to_dict()
# create an instance of PortfolioHistoricalValue from a dict
portfolio_historical_value_from_dict = PortfolioHistoricalValue.from_dict(portfolio_historical_value_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


