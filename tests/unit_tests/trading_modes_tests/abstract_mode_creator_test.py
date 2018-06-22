import math

from trading.trader.modes import AbstractTradingModeCreator


class TestAbstractTradingModeCreator:
    def test_adapt_price(self):
        pass

    def test_get_additional_dusts_to_quantity_if_necessary(self):
        pass

    def test_check_and_adapt_order_details_if_necessary(self):
        pass

    def test_can_create_order(self):
        pass

    def test_get_pre_order_data(self):
        pass

    def test_adapt_quantity(self):
        pass

    @staticmethod
    def test_trunc_with_n_decimal_digits():
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(1.00000000001, 10) == 1
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(1.00000000001, 11) == 1.00000000001
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 3) == 578
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 4) == 578.0001
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 7) == 578.000145
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 9) == 578.000145
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 10) == 578.0001450001
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 12) == 578.000145000156

    def test_get_value_or_default(self):
        test_dict = {"a": 1, "b": 2, "c": 3}
        assert AbstractTradingModeCreator._get_value_or_default(test_dict, "b", default="") == 2
        assert AbstractTradingModeCreator._get_value_or_default(test_dict, "d") is math.nan
        assert AbstractTradingModeCreator._get_value_or_default(test_dict, "d", default="") == ""

    def test_adapt_order_quantity_because_quantity(self):
        pass

    def test_adapt_order_quantity_because_price(self):
        pass
