import asyncio
import pytest


@pytest.fixture
def event_loop():
    """Use a new event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
