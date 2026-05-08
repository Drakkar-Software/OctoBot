import pytest

pytest.skip(
    reason="polymarket is not available in ccxt-rust; skip until a Rust implementation is added",
    allow_module_level=True,
)
