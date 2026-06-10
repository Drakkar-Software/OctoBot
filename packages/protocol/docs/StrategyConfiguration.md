# StrategyConfiguration


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration_type** | [**ActionConfigurationType**](ActionConfigurationType.md) | generic_workflow | 
**pair_settings** | [**List[MarketMakingSymbolConfiguration]**](MarketMakingSymbolConfiguration.md) |  | 
**symbols** | **List[str]** |  | 
**entry_order_amount** | **str** | Amout to buy, can be in %t, %s, in q, in base, etc | 
**exit_limit_orders_price_percent** | **float** |  | 
**entry_limit_orders_price_percent** | **float** |  | 
**secondary_entry_orders_count** | **float** |  | [default to 0]
**secondary_entry_orders_amount** | **str** | Amout to buy, can be in %t, %s, in q, in base, etc | [default to '0%t']
**secondary_entry_orders_price_percent** | **float** |  | [default to 10]
**enable_stop_loss** | **bool** |  | [optional] [default to False]
**stop_loss_price_discount_percent** | **float** |  | [optional] [default to 10]
**trigger_mode** | **str** |  | [optional] [default to 'Maximum evaluators signals based']
**use_init_entry_orders** | **bool** |  | [optional] [default to True]
**max_asset_holding_percent** | **float** |  | [optional] [default to 50]
**strategies** | [**List[StrategyEvaluatorConfiguration]**](StrategyEvaluatorConfiguration.md) |  | 
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


