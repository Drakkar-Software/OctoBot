from interfaces import get_bot


def get_symbol_time_frames(symbol, exchange_name):
    for exchange in get_bot().get_exchanges_list().values():
        if not exchange_name or exchange.get_name() == exchange_name:
            return exchange.get_exchange_manager().get_symbol_available_time_frames(symbol), exchange.get_name()
    return [], ""


def get_evaluation(symbol, exchange_name):
    try:
        if exchange_name:
            for exchange in get_bot().get_exchanges_list().values():
                if exchange.get_name() == exchange_name:
                    symbol_evaluator = get_bot().get_symbol_evaluator_list()[symbol]
                    return (
                        ",".join([
                            f"{dec.get_state().name}: {round(dec.get_final_eval(), 4)}"
                            if dec.get_state() is not None else "N/A"
                            for dec in symbol_evaluator.get_deciders(exchange)
                        ])
                    )
    except KeyError:
        return "N/A"
