# type: ignore
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
import contextlib
import mock
import os
import pytest
import tempfile

import tinydb

import octobot_commons.constants as constants
import octobot_commons.errors as errors
import octobot_commons.databases.document_database_adaptors.tinydb_adaptor as tinydb_adaptor

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


# ============== Fixtures and Helpers ==============

@contextlib.contextmanager
def get_temp_directory():
    """Context manager for creating a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@contextlib.asynccontextmanager
async def get_temp_database(cache_size=None):
    """Context manager for creating a temporary TinyDB database."""
    with get_temp_directory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_db.json")
        adaptor = tinydb_adaptor.TinyDBAdaptor(db_path, cache_size=cache_size)
        adaptor.initialize()
        try:
            yield adaptor
        finally:
            await adaptor.close()


# ============== Static Methods Tests ==============

def test_is_file_system_based():
    assert tinydb_adaptor.TinyDBAdaptor.is_file_system_based() is True


def test_get_db_file_ext():
    assert tinydb_adaptor.TinyDBAdaptor.get_db_file_ext() == constants.TINYDB_EXT
    assert tinydb_adaptor.TinyDBAdaptor.get_db_file_ext() == ".json"


# ============== Initialization Tests ==============

def test_init_sets_attributes():
    adaptor = tinydb_adaptor.TinyDBAdaptor("/some/path/db.json", cache_size=100)
    assert adaptor.db_path == "/some/path/db.json"
    assert adaptor.cache_size == 100
    assert adaptor.database is None


def test_init_with_default_cache_size():
    adaptor = tinydb_adaptor.TinyDBAdaptor("/some/path/db.json")
    assert adaptor.cache_size is None
    assert adaptor.database is None


def test_initialize_creates_database():
    with get_temp_directory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_db.json")
        adaptor = tinydb_adaptor.TinyDBAdaptor(db_path)
        adaptor.initialize()
        try:
            assert adaptor.database is not None
            assert isinstance(adaptor.database, tinydb.TinyDB)
        finally:
            adaptor.database.close()


def test_initialize_with_custom_cache_size():
    with get_temp_directory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_db.json")
        custom_cache_size = 1000
        adaptor = tinydb_adaptor.TinyDBAdaptor(db_path, cache_size=custom_cache_size)
        adaptor.initialize()
        try:
            assert adaptor.database is not None
            # Verify cache size was applied to the middleware
            assert adaptor.database.storage.WRITE_CACHE_SIZE == custom_cache_size
        finally:
            adaptor.database.close()


def test_initialize_uses_default_cache_size():
    with get_temp_directory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_db.json")
        adaptor = tinydb_adaptor.TinyDBAdaptor(db_path)
        adaptor.initialize()
        try:
            assert adaptor.database.storage.WRITE_CACHE_SIZE == tinydb_adaptor.TinyDBAdaptor.DEFAULT_WRITE_CACHE_SIZE
        finally:
            adaptor.database.close()


def test_initialize_raises_database_not_found_error():
    # Path with non-existent parent directory
    db_path = "/non/existent/path/db.json"
    adaptor = tinydb_adaptor.TinyDBAdaptor(db_path)
    with pytest.raises(errors.DatabaseNotFoundError):
        adaptor.initialize()


# ============== Identifier Operations Tests ==============

async def test_create_identifier():
    with get_temp_directory() as temp_dir:
        identifier_path = os.path.join(temp_dir, "new_identifier")
        assert not os.path.exists(identifier_path)
        await tinydb_adaptor.TinyDBAdaptor.create_identifier(identifier_path)
        assert os.path.exists(identifier_path)
        assert os.path.isdir(identifier_path)


async def test_identifier_exists_file():
    with get_temp_directory() as temp_dir:
        file_path = os.path.join(temp_dir, "test_file.json")
        # File doesn't exist yet
        assert await tinydb_adaptor.TinyDBAdaptor.identifier_exists(file_path, is_full_identifier=True) is False
        # Create file
        with open(file_path, "w") as f:
            f.write("{}")
        assert await tinydb_adaptor.TinyDBAdaptor.identifier_exists(file_path, is_full_identifier=True) is True


async def test_identifier_exists_directory():
    with get_temp_directory() as temp_dir:
        dir_path = os.path.join(temp_dir, "test_dir")
        # Directory doesn't exist yet
        assert await tinydb_adaptor.TinyDBAdaptor.identifier_exists(dir_path, is_full_identifier=False) is False
        # Create directory
        os.makedirs(dir_path)
        assert await tinydb_adaptor.TinyDBAdaptor.identifier_exists(dir_path, is_full_identifier=False) is True


async def test_get_sub_identifiers():
    with get_temp_directory() as temp_dir:
        # Create subdirectories
        os.makedirs(os.path.join(temp_dir, "sub1"))
        os.makedirs(os.path.join(temp_dir, "sub2"))
        os.makedirs(os.path.join(temp_dir, "ignored_sub"))
        # Create a file (should not be yielded)
        with open(os.path.join(temp_dir, "file.txt"), "w") as f:
            f.write("test")

        ignored = ["ignored_sub"]
        sub_identifiers = []
        async for name in tinydb_adaptor.TinyDBAdaptor.get_sub_identifiers(temp_dir, ignored):
            sub_identifiers.append(name)

        assert "sub1" in sub_identifiers
        assert "sub2" in sub_identifiers
        assert "ignored_sub" not in sub_identifiers
        assert "file.txt" not in sub_identifiers


async def test_get_single_sub_identifier_returns_name():
    with get_temp_directory() as temp_dir:
        # Create single subdirectory
        os.makedirs(os.path.join(temp_dir, "only_sub"))

        result = await tinydb_adaptor.TinyDBAdaptor.get_single_sub_identifier(temp_dir, [])
        assert result == "only_sub"


async def test_get_single_sub_identifier_returns_none_for_multiple():
    with get_temp_directory() as temp_dir:
        # Create multiple subdirectories
        os.makedirs(os.path.join(temp_dir, "sub1"))
        os.makedirs(os.path.join(temp_dir, "sub2"))

        result = await tinydb_adaptor.TinyDBAdaptor.get_single_sub_identifier(temp_dir, [])
        assert result is None


async def test_get_single_sub_identifier_returns_none_for_empty():
    with get_temp_directory() as temp_dir:
        result = await tinydb_adaptor.TinyDBAdaptor.get_single_sub_identifier(temp_dir, [])
        assert result is None


async def test_get_single_sub_identifier_ignores_specified():
    with get_temp_directory() as temp_dir:
        os.makedirs(os.path.join(temp_dir, "sub1"))
        os.makedirs(os.path.join(temp_dir, "ignored"))

        result = await tinydb_adaptor.TinyDBAdaptor.get_single_sub_identifier(temp_dir, ["ignored"])
        assert result == "sub1"


# ============== Document Operations Tests ==============

async def test_get_uuid():
    async with get_temp_database() as adaptor:
        doc_id = await adaptor.insert("test_table", {"name": "test"})
        documents = await adaptor.select("test_table", None)
        assert len(documents) == 1
        assert adaptor.get_uuid(documents[0]) == doc_id


async def test_select_all():
    async with get_temp_database() as adaptor:
        await adaptor.insert("test_table", {"name": "doc1"})
        await adaptor.insert("test_table", {"name": "doc2"})
        await adaptor.insert("test_table", {"name": "doc3"})

        results = await adaptor.select("test_table", None)
        assert len(results) == 3
        names = [doc["name"] for doc in results]
        assert "doc1" in names
        assert "doc2" in names
        assert "doc3" in names


async def test_select_with_query():
    async with get_temp_database() as adaptor:
        await adaptor.insert("test_table", {"name": "alice", "age": 30})
        await adaptor.insert("test_table", {"name": "bob", "age": 25})
        await adaptor.insert("test_table", {"name": "charlie", "age": 30})

        query = await adaptor.query_factory()
        results = await adaptor.select("test_table", query.age == 30)
        assert len(results) == 2
        names = [doc["name"] for doc in results]
        assert "alice" in names
        assert "charlie" in names


async def test_select_by_uuid():
    async with get_temp_database() as adaptor:
        doc1_id = await adaptor.insert("test_table", {"name": "doc1"})
        await adaptor.insert("test_table", {"name": "doc2"})

        result = await adaptor.select("test_table", None, uuid=doc1_id)
        assert result["name"] == "doc1"


async def test_tables():
    async with get_temp_database() as adaptor:
        await adaptor.insert("table1", {"data": 1})
        await adaptor.insert("table2", {"data": 2})
        await adaptor.insert("table3", {"data": 3})

        tables = await adaptor.tables()
        assert "table1" in tables
        assert "table2" in tables
        assert "table3" in tables


async def test_insert():
    async with get_temp_database() as adaptor:
        doc_id = await adaptor.insert("test_table", {"name": "test", "value": 42})
        assert isinstance(doc_id, int)
        assert doc_id > 0

        results = await adaptor.select("test_table", None)
        assert len(results) == 1
        assert results[0]["name"] == "test"
        assert results[0]["value"] == 42


async def test_insert_many():
    async with get_temp_database() as adaptor:
        rows = [
            {"name": "doc1", "value": 1},
            {"name": "doc2", "value": 2},
            {"name": "doc3", "value": 3},
        ]
        doc_ids = await adaptor.insert_many("test_table", rows)
        assert len(doc_ids) == 3
        assert all(isinstance(doc_id, int) for doc_id in doc_ids)

        results = await adaptor.select("test_table", None)
        assert len(results) == 3


async def test_upsert_insert():
    async with get_temp_database() as adaptor:
        query = await adaptor.query_factory()
        await adaptor.upsert("test_table", {"name": "new_doc", "value": 100}, query.name == "new_doc")

        results = await adaptor.select("test_table", None)
        assert len(results) == 1
        assert results[0]["name"] == "new_doc"
        assert results[0]["value"] == 100


async def test_upsert_update_with_query():
    async with get_temp_database() as adaptor:
        await adaptor.insert("test_table", {"name": "existing2", "value": 150})
        await adaptor.insert("test_table", {"name": "existing", "value": 50})

        query = await adaptor.query_factory()
        await adaptor.upsert("test_table", {"name": "existing", "value": 200}, query.name == "existing")

        query = await adaptor.query_factory()
        results = await adaptor.select("test_table", query.name == "existing")
        assert len(results) == 1
        assert results[0]["name"] == "existing"
        assert results[0]["value"] == 200


async def test_upsert_update_with_uuid():
    async with get_temp_database() as adaptor:
        doc_id = await adaptor.insert("test_table", {"name": "existing", "value": 50})

        await adaptor.upsert("test_table", {"name": "updated", "value": 300}, None, uuid=doc_id)

        result = await adaptor.select("test_table", None, uuid=doc_id)
        assert result["name"] == "updated"
        assert result["value"] == 300


async def test_update_with_query():
    async with get_temp_database() as adaptor:
        await adaptor.insert("test_table", {"name": "alice", "status": "active"})
        await adaptor.insert("test_table", {"name": "bob", "status": "active"})

        query = await adaptor.query_factory()
        await adaptor.update("test_table", {"status": "inactive"}, query.name == "alice")

        results = await adaptor.select("test_table", query.status == "inactive")
        assert len(results) == 1
        assert results[0]["name"] == "alice"


async def test_update_with_uuid():
    async with get_temp_database() as adaptor:
        doc_id = await adaptor.insert("test_table", {"name": "test", "value": 10})
        doc_id2 = await adaptor.insert("test_table", {"name": "test2", "value": 10})

        await adaptor.update("test_table", {"value": 999}, None, uuid=doc_id)

        result = await adaptor.select("test_table", None, uuid=doc_id)
        assert result["value"] == 999


async def test_update_many():
    async with get_temp_database() as adaptor:
        doc1_id = await adaptor.insert("test_table", {"name": "doc1", "value": 1})
        doc2_id = await adaptor.insert("test_table", {"name": "doc2", "value": 2})

        query = await adaptor.query_factory()
        update_values = [
            ({"value": 100}, query.name == "doc1"),
            ({"value": 200}, query.name == "doc2"),
        ]
        await adaptor.update_many("test_table", update_values)

        result1 = await adaptor.select("test_table", None, uuid=doc1_id)
        result2 = await adaptor.select("test_table", None, uuid=doc2_id)
        assert result1["value"] == 100
        assert result2["value"] == 200


async def test_delete_with_query():
    async with get_temp_database() as adaptor:
        await adaptor.insert("test_table", {"name": "keep", "type": "a"})
        await adaptor.insert("test_table", {"name": "delete", "type": "b"})

        query = await adaptor.query_factory()
        await adaptor.delete("test_table", query.type == "b")

        results = await adaptor.select("test_table", None)
        assert len(results) == 1
        assert results[0]["name"] == "keep"


async def test_delete_with_uuid():
    async with get_temp_database() as adaptor:
        doc1_id = await adaptor.insert("test_table", {"name": "doc1"})
        await adaptor.insert("test_table", {"name": "doc2"})

        await adaptor.delete("test_table", None, uuid=doc1_id)

        results = await adaptor.select("test_table", None)
        assert len(results) == 1
        assert results[0]["name"] == "doc2"


async def test_delete_drop_table():
    async with get_temp_database() as adaptor:
        await adaptor.insert("test_table", {"name": "doc1"})
        await adaptor.insert("test_table", {"name": "doc2"})
        await adaptor.insert("other_table", {"name": "other"})

        tables_before = await adaptor.tables()
        assert "test_table" in tables_before

        await adaptor.delete("test_table", None)

        tables_after = await adaptor.tables()
        assert "test_table" not in tables_after
        assert "other_table" in tables_after


async def test_count():
    async with get_temp_database() as adaptor:
        await adaptor.insert("test_table", {"name": "alice", "type": "user"})
        await adaptor.insert("test_table", {"name": "bob", "type": "user"})
        await adaptor.insert("test_table", {"name": "admin", "type": "admin"})

        query = await adaptor.query_factory()
        user_count = await adaptor.count("test_table", query.type == "user")
        admin_count = await adaptor.count("test_table", query.type == "admin")

        assert user_count == 2
        assert admin_count == 1


async def test_query_factory():
    async with get_temp_database() as adaptor:
        query = await adaptor.query_factory()
        assert isinstance(query, tinydb.Query)


# ============== Lifecycle Operations Tests ==============

async def test_hard_reset():
    with get_temp_directory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_db.json")
        adaptor = tinydb_adaptor.TinyDBAdaptor(db_path)
        adaptor.initialize()

        # Insert some data
        await adaptor.insert("test_table", {"name": "test"})
        await adaptor.flush()

        # Verify file exists
        assert os.path.exists(db_path)

        # Hard reset with mocked close and initialize to verify they are called
        with mock.patch.object(adaptor, "close", wraps=adaptor.close) as mock_close, \
             mock.patch.object(adaptor, "initialize", wraps=adaptor.initialize) as mock_initialize:
            await adaptor.hard_reset()
            mock_close.assert_called_once()
            mock_initialize.assert_called_once()

        # Verify database was reset (file recreated, empty tables)
        tables = await adaptor.tables()
        assert "test_table" not in tables or len(await adaptor.select("test_table", None)) == 0

        await adaptor.close()


async def test_flush():
    with get_temp_directory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_db.json")
        adaptor = tinydb_adaptor.TinyDBAdaptor(db_path)
        adaptor.initialize()

        try:
            await adaptor.insert("test_table", {"name": "test"})
            # Flush should not raise
            await adaptor.flush()
        finally:
            await adaptor.close()


async def test_close():
    with get_temp_directory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_db.json")
        adaptor = tinydb_adaptor.TinyDBAdaptor(db_path)
        adaptor.initialize()

        await adaptor.insert("test_table", {"name": "test"})
        # Close should not raise
        await adaptor.close()


async def test_close_handles_attribute_error():
    adaptor = tinydb_adaptor.TinyDBAdaptor("/some/path/db.json")
    # database is None, close should handle AttributeError gracefully
    await adaptor.close()  # Should not raise


async def test_close_handles_type_error():
    with get_temp_directory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_db.json")
        adaptor = tinydb_adaptor.TinyDBAdaptor(db_path)
        adaptor.initialize()

        # Mock the database.close to raise TypeError
        with mock.patch.object(adaptor.database, "close", side_effect=TypeError("test error")):
            # Should not raise, but log the error
            await adaptor.close()


# ============== LazyJSONStorage Tests ==============

def test_lazy_storage_does_not_create_file_on_init():
    with get_temp_directory() as temp_dir:
        db_path = os.path.join(temp_dir, "lazy_test.json")
        LazyJSONStorage = tinydb_adaptor.TinyDBAdaptor._get_storage()
        storage = LazyJSONStorage(db_path)

        # File should not exist yet
        assert not os.path.exists(db_path)
        storage.close()


def test_lazy_storage_creates_file_on_handle_access():
    with get_temp_directory() as temp_dir:
        db_path = os.path.join(temp_dir, "lazy_test.json")
        LazyJSONStorage = tinydb_adaptor.TinyDBAdaptor._get_storage()
        storage = LazyJSONStorage(db_path)

        assert not os.path.exists(db_path)

        # Access _handle to trigger file creation
        _ = storage._handle

        assert os.path.exists(db_path)
        storage.close()


def test_lazy_storage_close_without_open():
    with get_temp_directory() as temp_dir:
        db_path = os.path.join(temp_dir, "lazy_test.json")
        LazyJSONStorage = tinydb_adaptor.TinyDBAdaptor._get_storage()
        storage = LazyJSONStorage(db_path)

        # Close without ever opening - should not raise
        storage.close()
        assert not os.path.exists(db_path)


def test_lazy_storage_raises_file_not_found_for_missing_parent():
    LazyJSONStorage = tinydb_adaptor.TinyDBAdaptor._get_storage()
    with pytest.raises(FileNotFoundError):
        LazyJSONStorage("/non/existent/path/db.json")


# ============== Functional Integration Test ==============

async def test_full_workflow_functional():
    """
    Comprehensive functional test exercising most TinyDBAdaptor methods
    without any mocks - using real TinyDB operations.
    """
    with get_temp_directory() as temp_dir:
        # 1. Create identifier (directory structure)
        identifier_path = os.path.join(temp_dir, "data", "exchange1")
        await tinydb_adaptor.TinyDBAdaptor.create_identifier(identifier_path)
        assert os.path.isdir(identifier_path)

        # 2. Verify identifier_exists for directory
        assert await tinydb_adaptor.TinyDBAdaptor.identifier_exists(
            identifier_path, is_full_identifier=False
        ) is True

        # 3. Initialize database
        db_path = os.path.join(identifier_path, "database.json")
        adaptor = tinydb_adaptor.TinyDBAdaptor(db_path, cache_size=100)
        adaptor.initialize()

        try:
            # 4. Verify static methods
            assert tinydb_adaptor.TinyDBAdaptor.is_file_system_based() is True
            assert tinydb_adaptor.TinyDBAdaptor.get_db_file_ext() == ".json"

            # 5. Insert documents into multiple tables

            # 5.a: Verify database file does not exist (lazy initialization)
            db_path = os.path.join(identifier_path, "database.json")
            assert not os.path.exists(db_path)
            user1_id = await adaptor.insert("users", {"name": "Alice", "age": 30, "role": "admin"})
            # 5.b: Verify database file NOW exists (lazy initialization tirggered)
            assert os.path.exists(db_path)

            user2_id = await adaptor.insert("users", {"name": "Bob", "age": 25, "role": "user"})
            user3_id = await adaptor.insert("users", {"name": "Charlie", "age": 35, "role": "user"})

            order_ids = await adaptor.insert_many("orders", [
                {"user_id": user1_id, "product": "Widget", "quantity": 5},
                {"user_id": user2_id, "product": "Gadget", "quantity": 3},
                {"user_id": user1_id, "product": "Gizmo", "quantity": 2},
            ])
            assert len(order_ids) == 3

            # 6. Select all and verify
            all_users = await adaptor.select("users", None)
            assert len(all_users) == 3

            all_orders = await adaptor.select("orders", None)
            assert len(all_orders) == 3

            # 7. Query with tinydb.Query
            query = await adaptor.query_factory()
            admins = await adaptor.select("users", query.role == "admin")
            assert len(admins) == 1
            assert admins[0]["name"] == "Alice"

            users_over_25 = await adaptor.select("users", query.age > 25)
            assert len(users_over_25) == 2

            # 8. Select by UUID
            user1_doc = await adaptor.select("users", None, uuid=user1_id)
            assert user1_doc["name"] == "Alice"

            # 9. Get UUID from document
            assert adaptor.get_uuid(all_users[0]) > 0

            # 10. Upsert - insert new
            await adaptor.upsert("users", {"name": "Diana", "age": 28, "role": "user"}, query.name == "Diana")
            all_users = await adaptor.select("users", None)
            assert len(all_users) == 4

            # 11. Upsert - update existing by query
            await adaptor.upsert("users", {"name": "Alice", "age": 31, "role": "superadmin"}, query.name == "Alice")
            alice = await adaptor.select("users", query.name == "Alice")
            assert alice[0]["age"] == 31
            assert alice[0]["role"] == "superadmin"

            # 12. Upsert - update existing by UUID
            await adaptor.upsert("users", {"name": "Bob", "age": 26, "role": "moderator"}, None, uuid=user2_id)
            bob = await adaptor.select("users", None, uuid=user2_id)
            assert bob["age"] == 26
            assert bob["role"] == "moderator"

            # 13. Update by query
            await adaptor.update("orders", {"status": "pending"}, query.product == "Widget")
            widget_orders = await adaptor.select("orders", query.product == "Widget")
            assert widget_orders[0]["status"] == "pending"

            # 14. Update by UUID
            await adaptor.update("orders", {"status": "shipped"}, None, uuid=order_ids[0])
            order = await adaptor.select("orders", None, uuid=order_ids[0])
            assert order["status"] == "shipped"

            # 15. Update many
            await adaptor.update_many("orders", [
                ({"priority": "high"}, query.user_id == user1_id),
                ({"priority": "normal"}, query.user_id == user2_id),
            ])
            high_priority = await adaptor.select("orders", query.priority == "high")
            assert len(high_priority) == 2  # Alice has 2 orders

            # 16. Count documents
            user_count = await adaptor.count("users", query.role != "superadmin")
            assert user_count == 3

            total_orders = await adaptor.count("orders", query.quantity >= 1)
            assert total_orders == 3

            # 17. Get tables list
            tables = await adaptor.tables()
            assert "users" in tables
            assert "orders" in tables

            # 18. Delete by query
            await adaptor.delete("orders", query.product == "Gizmo")
            remaining_orders = await adaptor.select("orders", None)
            assert len(remaining_orders) == 2

            # 19. Delete by UUID
            await adaptor.delete("users", None, uuid=user3_id)
            remaining_users = await adaptor.select("users", None)
            assert len(remaining_users) == 3
            charlie = await adaptor.select("users", query.name == "Charlie")
            assert len(charlie) == 0

            # 20. Delete (drop table)
            await adaptor.delete("orders", None)
            tables = await adaptor.tables()
            assert "orders" not in tables
            assert "users" in tables

            # 21. Flush to ensure data is written
            await adaptor.flush()

            # 22. Verify identifier_exists for file
            assert await tinydb_adaptor.TinyDBAdaptor.identifier_exists(
                db_path, is_full_identifier=True
            ) is True

            # 23. Hard reset
            await adaptor.hard_reset()

            # 24. Verify database is empty after reset
            tables_after_reset = await adaptor.tables()
            assert "users" not in tables_after_reset

            # 25. Verify we can still use the database after reset
            await adaptor.insert("new_table", {"data": "after_reset"})
            new_data = await adaptor.select("new_table", None)
            assert len(new_data) == 1
            assert new_data[0]["data"] == "after_reset"

            # 26. Test get_sub_identifiers
            os.makedirs(os.path.join(temp_dir, "data", "exchange2"))
            os.makedirs(os.path.join(temp_dir, "data", "ignored_exchange"))
            sub_ids = []
            async for sub_id in tinydb_adaptor.TinyDBAdaptor.get_sub_identifiers(
                os.path.join(temp_dir, "data"), ["ignored_exchange"]
            ):
                sub_ids.append(sub_id)
            assert "exchange1" in sub_ids
            assert "exchange2" in sub_ids
            assert "ignored_exchange" not in sub_ids

            # 27. Test get_single_sub_identifier
            single_sub = await tinydb_adaptor.TinyDBAdaptor.get_single_sub_identifier(
                identifier_path, []
            )
            # Should return None since there are no subdirectories in exchange1
            assert single_sub is None

        finally:
            # 28. Close database
            await adaptor.close()

        # 29. Verify file still exists after close
        assert os.path.exists(db_path)
