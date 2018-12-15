from config.config import load_config


def test_load_config():
    result = load_config("tests/static/config.json")
    assert "crypto-currencies" in result
    assert "services" in result
    assert "exchanges" in result
    assert "trading" in result
    assert "Bitcoin" in result["crypto-currencies"]


def test_load_config_without_file(caplog):
    load_config("tests/static/test_config.json", error=False)
    assert 'file opening failed' in caplog.text


def test_load_config_incorrect(caplog):
    load_config("tests/unit_tests/tools_tests/incorrect_config_file.txt", error=False)
    assert 'json decoding failed' in caplog.text
