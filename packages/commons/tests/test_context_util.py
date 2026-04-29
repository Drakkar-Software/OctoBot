#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import pytest

import octobot_commons.context_util as context_util


def test_empty_context_manager_sync_enter_exit():
    """Test EmptyContextManager as synchronous context manager"""
    manager = context_util.EmptyContextManager()
    
    # Test that __enter__ returns self
    with manager as ctx:
        assert ctx is manager
        # Verify we can use it normally
        assert ctx is not None


def test_empty_context_manager_sync_no_exception_suppression():
    """Test that EmptyContextManager doesn't suppress exceptions"""
    manager = context_util.EmptyContextManager()
    
    # Exception should propagate normally
    with pytest.raises(ValueError):
        with manager:
            raise ValueError("Test exception")


def test_empty_context_manager_sync_multiple_usage():
    """Test EmptyContextManager can be used multiple times"""
    manager = context_util.EmptyContextManager()
    
    # First usage
    with manager as ctx1:
        assert ctx1 is manager
    
    # Second usage
    with manager as ctx2:
        assert ctx2 is manager


def test_empty_context_manager_sync_exit_with_exception():
    """Test EmptyContextManager __exit__ with exception"""
    manager = context_util.EmptyContextManager()
    
    # __exit__ should not suppress exceptions (returns None/False)
    with pytest.raises(ValueError):
        with manager:
            raise ValueError("Test exception")
    
    # Verify exception was not suppressed
    try:
        with manager:
            raise ValueError("Another exception")
    except ValueError as e:
        assert str(e) == "Another exception"


def test_empty_context_manager_sync_exit_without_exception():
    """Test EmptyContextManager __exit__ without exception"""
    manager = context_util.EmptyContextManager()
    
    # Normal exit should work fine
    with manager:
        pass
    
    # Should complete without issues
    assert True


@pytest.mark.asyncio
async def test_empty_context_manager_async_enter_exit():
    """Test EmptyContextManager as asynchronous context manager"""
    manager = context_util.EmptyContextManager()
    
    # Test that __aenter__ returns self
    async with manager as ctx:
        assert ctx is manager
        # Verify we can use it normally
        assert ctx is not None


@pytest.mark.asyncio
async def test_empty_context_manager_async_no_exception_suppression():
    """Test that EmptyContextManager doesn't suppress exceptions in async context"""
    manager = context_util.EmptyContextManager()
    
    # Exception should propagate normally
    with pytest.raises(ValueError):
        async with manager:
            raise ValueError("Test async exception")


@pytest.mark.asyncio
async def test_empty_context_manager_async_multiple_usage():
    """Test EmptyContextManager can be used multiple times in async context"""
    manager = context_util.EmptyContextManager()
    
    # First usage
    async with manager as ctx1:
        assert ctx1 is manager
    
    # Second usage
    async with manager as ctx2:
        assert ctx2 is manager


@pytest.mark.asyncio
async def test_empty_context_manager_async_exit_with_exception():
    """Test EmptyContextManager __aexit__ with exception"""
    manager = context_util.EmptyContextManager()
    
    # __aexit__ should not suppress exceptions (returns None/False)
    with pytest.raises(ValueError):
        async with manager:
            raise ValueError("Test async exception")
    
    # Verify exception was not suppressed
    try:
        async with manager:
            raise ValueError("Another async exception")
    except ValueError as e:
        assert str(e) == "Another async exception"


@pytest.mark.asyncio
async def test_empty_context_manager_async_exit_without_exception():
    """Test EmptyContextManager __aexit__ without exception"""
    manager = context_util.EmptyContextManager()
    
    # Normal exit should work fine
    async with manager:
        pass
    
    # Should complete without issues
    assert True


@pytest.mark.asyncio
async def test_empty_context_manager_mixed_sync_async():
    """Test EmptyContextManager can be used both synchronously and asynchronously"""
    manager = context_util.EmptyContextManager()
    
    # Use synchronously
    with manager:
        pass
    
    # Use asynchronously
    async with manager:
        pass
    
    # Both should work without issues
    assert True
