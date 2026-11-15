#  Drakkar-Software OctoBot-Services

import datetime

import octobot_protocol.models as protocol_models

import octobot_node.protocol.automations as automations_protocol
import octobot_services.interfaces.bots.node_command_format as node_command_format

_SAMPLE_TIMESTAMP = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)


def _read_view(name: str, symbol: str) -> automations_protocol.AutomationReadView:
    automation = protocol_models.AutomationState(
        id="auto-1",
        status=protocol_models.WorkflowStatus.RUNNING,
        metadata=protocol_models.AutomationMetadata(
            name=name,
            description="",
            created_at=_SAMPLE_TIMESTAMP,
            updated_at=_SAMPLE_TIMESTAMP,
        ),
        exchanges=["binance"],
    )
    trade = protocol_models.Trade(
        id="trade-1",
        trade_id="trade-1",
        type=protocol_models.OrderType.LIMIT,
        symbol=symbol,
        side=protocol_models.Side.BUY,
        quantity=1.0,
        price=50.0,
        fee=protocol_models.Fee(amount=0.01, currency="USDT"),
        status=protocol_models.OrderStatus.FILLED,
        executed_at=_SAMPLE_TIMESTAMP,
    )
    order = protocol_models.Order(
        id="order-1",
        symbol=symbol,
        price=50.0,
        quantity=1.0,
        filled=0.0,
        exchange_id="binance",
        side=protocol_models.Side.SELL,
        type=protocol_models.OrderType.LIMIT,
        status=protocol_models.OrderStatus.OPEN,
        created_at=_SAMPLE_TIMESTAMP,
    )
    return automations_protocol.AutomationReadView(
        user_id="wallet-user",
        automation=automation,
        orders=[order],
        trades=[trade],
        fees_by_currency={"USDT": 0.01},
    )


class TestFormatFeesMessage:
    def test_includes_automation_name_and_fees(self):
        view = _read_view("MyBot", "BTC/USDT")
        message = node_command_format.format_fees_message([view], view)
        assert "MyBot" in message
        assert "USDT" in message


class TestFormatOpenOrdersMessage:
    def test_includes_automation_name_and_symbol(self):
        view = _read_view("MyBot", "BTC/USDT")
        message = node_command_format.format_open_orders_message([view], view)
        assert "MyBot" in message
        plain = message.replace("*", "").replace("`", "")
        assert "MyBot Open orders:" in plain
        assert "BTC/USDT" in message


class TestFormatPortfolioMessage:
    def test_includes_grouped_asset_symbol(self):
        view = _read_view("MyBot", "BTC/USDT")
        view = automations_protocol.AutomationReadView(
            user_id=view.user_id,
            automation=protocol_models.AutomationState(
                id=view.automation.id,
                status=view.automation.status,
                metadata=view.automation.metadata,
                assets=[
                    protocol_models.DetailedAssetsForTradingType(
                        trading_type=protocol_models.TradingType.SPOT,
                        assets=[
                            protocol_models.DetailedAsset(
                                symbol="BTC",
                                total=2.0,
                                available=1.0,
                            )
                        ],
                    )
                ],
            ),
            orders=view.orders,
            trades=view.trades,
            fees_by_currency=view.fees_by_currency,
        )
        message = node_command_format.format_portfolio_message([view], view)
        assert "MyBot" in message
        assert "BTC" in message


class TestFormatTradesHistoryMessage:
    def test_includes_automation_name_and_trade_symbol(self):
        view = _read_view("MyBot", "ETH/USDT")
        message = node_command_format.format_trades_history_message([view], view)
        assert "MyBot" in message
        plain = message.replace("*", "").replace("`", "")
        assert "MyBot Trades:" in plain
        assert "ETH/USDT" in message