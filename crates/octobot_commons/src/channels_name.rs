use crate::str_enum;

str_enum! {
    pub enum OctoBotChannelsName {
        OctoBotChannel => "OctoBot",
    }
}

str_enum! {
    pub enum OctoBotUserChannelsName {
        UserCommandsChannel => "UserCommands",
    }
}

str_enum! {
    pub enum OctoBotEvaluatorsChannelsName {
        MatrixChannel => "Matrix",
        EvaluatorsChannel => "Evaluators",
    }
}

str_enum! {
    pub enum OctoBotBacktestingChannelsName {
        TimeChannel => "Time",
    }
}

str_enum! {
    pub enum OctoBotCommunityChannelsName {
        RemoteTradingSignalsChannel => "RemoteTradingSignals",
    }
}

str_enum! {
    pub enum OctoBotTradingChannelsName {
        OhlcvChannel => "OHLCV",
        TickerChannel => "Ticker",
        MiniTickerChannel => "MiniTicker",
        RecentTradesChannel => "RecentTrade",
        OrderBookChannel => "OrderBook",
        OrderBookTickerChannel => "OrderBookTicker",
        KlineChannel => "Kline",
        TradesChannel => "Trades",
        LiquidationsChannel => "Liquidations",
        OrdersChannel => "Orders",
        BalanceChannel => "Balance",
        BalanceProfitabilityChannel => "BalanceProfitability",
        PositionsChannel => "Positions",
        ModeChannel => "Mode",
        MarkPriceChannel => "MarkPrice",
        FundingChannel => "Funding",
        MarketsChannel => "Markets",
    }
}
