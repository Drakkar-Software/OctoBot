# PortfolioContent

PortfolioContent

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**total** | **float** |  | 
**unit** | **str** |  | 
**assets** | [**List[DetailedAsset]**](DetailedAsset.md) |  | 

## Example

```python
from octobot_protocol.models.portfolio_content import PortfolioContent

# TODO update the JSON string below
json = "{}"
# create an instance of PortfolioContent from a JSON string
portfolio_content_instance = PortfolioContent.from_json(json)
# print the JSON string representation of the object
print(PortfolioContent.to_json())

# convert the object into a dict
portfolio_content_dict = portfolio_content_instance.to_dict()
# create an instance of PortfolioContent from a dict
portfolio_content_from_dict = PortfolioContent.from_dict(portfolio_content_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


