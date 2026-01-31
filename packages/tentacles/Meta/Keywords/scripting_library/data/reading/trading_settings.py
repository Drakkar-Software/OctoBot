def set_initialized_evaluation(ctx, trading_mode, initialized=True, symbol=None, time_frame=None):
    trading_mode.set_initialized_trading_pair_by_bot_id(symbol or ctx.symbol, time_frame or ctx.time_frame, initialized)


def get_initialized_evaluation(ctx, trading_mode, symbol=None, time_frame=None):
    return trading_mode.get_initialized_trading_pair_by_bot_id(symbol or ctx.symbol, time_frame or ctx.time_frame)


def are_all_evaluation_initialized(ctx, trading_mode):
    for symbol in ctx.exchange_manager.exchange_config.traded_symbol_pairs:
        for time_frame in ctx.exchange_manager.exchange_config.get_relevant_time_frames():
            try:
                if not get_initialized_evaluation(ctx, trading_mode, symbol=symbol, time_frame=time_frame.value):
                    return False
            except KeyError:
                return False
    return True
