import pytest

import octobot_flow.errors
import octobot_flow.parsers.signal_script_resolver as signal_script_resolver
import octobot_trading.enums as trading_enums


EXCHANGE_NAME = "binance"
EXCHANGE_TYPE = trading_enums.ExchangeTypes.SPOT
REFERENCE_MARKET = "USDT"

SIGNAL_BUY_KEYVAL = "SYMBOL=BTC/USDC\nSIGNAL=buy\nVOLUME=0.01"
SIGNAL_CANCEL_KEYVAL = "SYMBOL=BTC/USDC\nSIGNAL=cancel"
SIGNAL_SELL_JSON = '{"SYMBOL":"BTC/USDC","SIGNAL":"sell","VOLUME":0.01}'
SIGNAL_BUY_DICT = {"SYMBOL": "BTC/USDC", "SIGNAL": "buy", "VOLUME": 0.01}

RESOLVER_KWARGS = dict(
    exchange_name=EXCHANGE_NAME,
    exchange_type=EXCHANGE_TYPE,
    reference_market=REFERENCE_MARKET,
    ignore_exchange_key=True,
)


def _resolve(script):
    return signal_script_resolver.resolve_signal_script(script, **RESOLVER_KWARGS)


class TestResolveSignalScriptKeyvalString:
    def test_buy_market_signal(self):
        dsl_script = _resolve(SIGNAL_BUY_KEYVAL)
        assert "market" in dsl_script
        assert "buy" in dsl_script
        assert "BTC/USDC" in dsl_script
        assert "0.01" in dsl_script

    def test_cancel_signal(self):
        dsl_script = _resolve(SIGNAL_CANCEL_KEYVAL)
        assert dsl_script.startswith("cancel_order(")

    def test_ignores_exchange_key(self):
        with_exchange = f"EXCHANGE=wrong\n{SIGNAL_BUY_KEYVAL}"
        assert _resolve(with_exchange) == _resolve(SIGNAL_BUY_KEYVAL)

    def test_usd_star_symbol_adaptation(self):
        dsl_script = _resolve("SYMBOL=BTC/USD*\nSIGNAL=buy\nVOLUME=0.01")
        assert "BTC/USDC" in dsl_script
        assert "USD*" not in dsl_script

    def test_param_val_is_not_dsl_passthrough(self):
        invalid_script = "SYMBOL=BTC/USDC\nSIGNAL=not_a_signal"
        with pytest.raises(octobot_flow.errors.InvalidAutomationActionError):
            _resolve(invalid_script)

    def test_param_val_shape_never_passthrough_even_with_equals(self):
        with pytest.raises(octobot_flow.errors.InvalidAutomationActionError):
            _resolve("side=buy\namount=0.01")


class TestResolveSignalScriptJsonString:
    def test_sell_from_json_string(self):
        dsl_script = _resolve(SIGNAL_SELL_JSON)
        assert "sell" in dsl_script


class TestResolveSignalScriptDict:
    def test_buy_from_dict(self):
        keyval_dsl = _resolve(SIGNAL_BUY_KEYVAL)
        dict_dsl = _resolve(SIGNAL_BUY_DICT)
        for dsl_script in (keyval_dsl, dict_dsl):
            assert "market" in dsl_script
            assert "buy" in dsl_script
            assert "BTC/USDC" in dsl_script
            assert "0.01" in dsl_script


class TestResolveSignalScriptDslPassthrough:
    def test_returns_dsl_unchanged(self):
        dsl_script = _resolve("market('buy', 'BTC/USDC', 0.01)")
        assert dsl_script == "market('buy', 'BTC/USDC', 0.01)"

    def test_non_keyval_string_without_equals(self):
        dsl_script = _resolve("stop_automation()")
        assert dsl_script == "stop_automation()"


class TestResolveSignalScriptErrors:
    def test_missing_symbol_raises(self):
        with pytest.raises(octobot_flow.errors.InvalidAutomationActionError):
            _resolve("SIGNAL=buy\nVOLUME=1")

    def test_unknown_signal_raises(self):
        with pytest.raises(octobot_flow.errors.InvalidAutomationActionError):
            _resolve("SYMBOL=BTC/USDC\nSIGNAL=not_a_signal\nVOLUME=1")

    def test_empty_string_raises(self):
        with pytest.raises(octobot_flow.errors.InvalidAutomationActionError):
            _resolve("")

    def test_invalid_keyval_does_not_fallback_to_dsl(self):
        with pytest.raises(octobot_flow.errors.InvalidAutomationActionError):
            _resolve("SIGNAL=bad\nnot=valid=dsl")

    def test_invalid_json_does_not_fallback_to_dsl(self):
        with pytest.raises(octobot_flow.errors.InvalidAutomationActionError):
            _resolve('{"SYMBOL":"BTC/USDC","SIGNAL":')
