# StrategyConfiguration


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | **str** |  | 
**pair_settings** | [**List[MarketMakingSymbolConfiguration]**](MarketMakingSymbolConfiguration.md) |  | 
**symbols** | **List[str]** |  | 
**buy_orders_count** | **float** |  | 
**percent_amount_per_buy_order** | **float** |  | 
**profit_target_percent** | **float** |  | 
**buy_order_price_discount_percent** | **float** |  | 
**enable_stop_loss** | **bool** |  | [default to False]
**stop_loss_price_discount_percent** | **float** |  | 
**trigger_mode** | **str** |  | 
**use_init_entry_orders** | **bool** |  | [default to True]
**time_frames** | [**List[TimeFrame]**](TimeFrame.md) |  | 
**evaluators** | [**List[EvaluatorConfiguration]**](EvaluatorConfiguration.md) |  | 
**coins** | [**List[IndexCoin]**](IndexCoin.md) |  | 
**rebalance_trigger_min_percent** | **float** |  | 
**symbol** | **str** |  | 
**spread** | **float** | Price difference between the closest buy and sell orders. Denominated in the quote currency (600 for a 600 USDT spread on BTC/USDT). | 
**increment** | **float** | Price difference between two orders of the same side. Denominated in the quote currency (200 for a 200 USDT spread on BTC/USDT). | 
**buy_count** | **float** | Number of initial buy orders to create. Make sure to have enough funds to create that many orders. | 
**sell_count** | **float** | Number of initial sell orders to create. Make sure to have enough funds to create that many orders. | 
**enable_trailing_up** | **bool** |  | [default to True]
**enable_trailing_down** | **bool** |  | [default to False]
**order_by_order_trailing** | **bool** |  | [default to True]
**strategy_id** | **str** |  | 
**profile_data** | **object** |  | 
**actions** | [**List[Action]**](Action.md) |  | 

## Example

```python
from octobot_protocol.models.strategy_configuration import StrategyConfiguration

# TODO update the JSON string below
json = "{}"
# create an instance of StrategyConfiguration from a JSON string
strategy_configuration_instance = StrategyConfiguration.from_json(json)
# print the JSON string representation of the object
print(StrategyConfiguration.to_json())

# convert the object into a dict
strategy_configuration_dict = strategy_configuration_instance.to_dict()
# create an instance of StrategyConfiguration from a dict
strategy_configuration_from_dict = StrategyConfiguration.from_dict(strategy_configuration_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


