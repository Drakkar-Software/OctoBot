use octobot_commons::channels_name::*;

#[test]
fn test_octobot_channel_value() {
    assert_eq!(OctoBotChannelsName::OctoBotChannel.value(), "OctoBot");
}

#[test]
fn test_user_commands_channel_value() {
    assert_eq!(
        OctoBotUserChannelsName::UserCommandsChannel.value(),
        "UserCommands"
    );
}

#[test]
fn test_ohlcv_channel_value() {
    assert_eq!(
        OctoBotTradingChannelsName::OhlcvChannel.value(),
        "OHLCV"
    );
}

#[test]
fn test_ticker_channel_value() {
    assert_eq!(
        OctoBotTradingChannelsName::TickerChannel.value(),
        "Ticker"
    );
}

#[test]
fn test_orders_channel_value() {
    assert_eq!(
        OctoBotTradingChannelsName::OrdersChannel.value(),
        "Orders"
    );
}

#[test]
fn test_matrix_channel_value() {
    assert_eq!(
        OctoBotEvaluatorsChannelsName::MatrixChannel.value(),
        "Matrix"
    );
}

#[test]
fn test_time_channel_value() {
    assert_eq!(
        OctoBotBacktestingChannelsName::TimeChannel.value(),
        "Time"
    );
}

#[test]
fn test_remote_trading_signals_channel_value() {
    assert_eq!(
        OctoBotCommunityChannelsName::RemoteTradingSignalsChannel.value(),
        "RemoteTradingSignals"
    );
}

// ---------------------------------------------------------------------------
// from_value round-trips
// ---------------------------------------------------------------------------

#[test]
fn test_octobot_channels_name_round_trip() {
    let val = OctoBotChannelsName::OctoBotChannel.value();
    assert_eq!(
        OctoBotChannelsName::from_value(val),
        Some(OctoBotChannelsName::OctoBotChannel)
    );
}

#[test]
fn test_user_channels_name_round_trip() {
    let val = OctoBotUserChannelsName::UserCommandsChannel.value();
    assert_eq!(
        OctoBotUserChannelsName::from_value(val),
        Some(OctoBotUserChannelsName::UserCommandsChannel)
    );
}

#[test]
fn test_trading_channels_name_round_trip() {
    let val = OctoBotTradingChannelsName::OhlcvChannel.value();
    assert_eq!(
        OctoBotTradingChannelsName::from_value(val),
        Some(OctoBotTradingChannelsName::OhlcvChannel)
    );
}

#[test]
fn test_evaluators_channels_name_round_trip() {
    let val = OctoBotEvaluatorsChannelsName::MatrixChannel.value();
    assert_eq!(
        OctoBotEvaluatorsChannelsName::from_value(val),
        Some(OctoBotEvaluatorsChannelsName::MatrixChannel)
    );
}

#[test]
fn test_backtesting_channels_name_round_trip() {
    let val = OctoBotBacktestingChannelsName::TimeChannel.value();
    assert_eq!(
        OctoBotBacktestingChannelsName::from_value(val),
        Some(OctoBotBacktestingChannelsName::TimeChannel)
    );
}

#[test]
fn test_community_channels_name_round_trip() {
    let val = OctoBotCommunityChannelsName::RemoteTradingSignalsChannel.value();
    assert_eq!(
        OctoBotCommunityChannelsName::from_value(val),
        Some(OctoBotCommunityChannelsName::RemoteTradingSignalsChannel)
    );
}
