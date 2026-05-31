"""Tests for octobot_sync.server (excluding helpers already covered by test_server_helpers.py)."""

import json
import os

from unittest import mock
import pytest

import octobot_sync.crypto as sync_crypto
import octobot_sync.server as server
import octobot_sync.enums as enums
import octobot_sync.errors as errors

from starfish_server.storage.base import StoreContext
from starfish_server.storage.s3 import S3ObjectStore
from starfish_server.storage.filesystem import FilesystemObjectStore


_TEST_WALLET_PRIVATE_KEY = "test-server-private-key"


def _make_context(
    identity: str | None = "0xabc",
    action: str = "pull",
    collection: str = "test",
    params: dict | None = None,
) -> StoreContext:
    return StoreContext(
        collection=collection,
        params=params or {},
        identity=identity,
        roles=(),
        action=action,
    )


class TestGetIdentity:
    def test_returns_identity_when_present(self):
        context = _make_context(identity="0xabc")
        assert server._get_identity(context) == "0xabc"

    def test_raises_when_context_is_none(self):
        with pytest.raises(errors.OctobotSyncIdentityMissingError):
            server._get_identity(None)

    def test_raises_when_identity_is_none(self):
        context = _make_context(identity=None)
        with pytest.raises(errors.OctobotSyncIdentityMissingError):
            server._get_identity(context)


class TestGetData:
    @pytest.mark.asyncio
    async def test_user_data_collection(self):
        expected_plain = json.dumps({"version": "1", "automations": [], "user_actions": []})
        stub_state = mock.MagicMock()
        stub_state.to_json.return_value = expected_plain
        context = _make_context(identity="0xwallet", collection=enums.Collections.USER_DATA.value)
        with (
            mock.patch("octobot_sync.server.user_data_protocol") as mock_proto,
            mock.patch(
                "octobot_sync.server._get_wallet_private_key",
                return_value=_TEST_WALLET_PRIVATE_KEY,
            ),
        ):
            mock_proto.get_user_data_state = mock.AsyncMock(return_value=stub_state)
            result = await server.get_data("users/0xwallet/data", context)
        mock_proto.get_user_data_state.assert_awaited_once_with("0xwallet")
        wrapper = json.loads(result)
        assert wrapper["v"] == 1
        assert wrapper["timestamps"] == {}
        assert wrapper["hash"] == sync_crypto.sha256_hex(expected_plain)
        decrypted = sync_crypto.decrypt_wire_to_utf8_json(
            wrapper["data"],
            _TEST_WALLET_PRIVATE_KEY,
            enums.Collections.USER_DATA.value,
        )
        assert decrypted == expected_plain

    @pytest.mark.asyncio
    async def test_user_data_hash_is_stable_across_pulls(self):
        """Two pulls of identical state must produce identical hashes (stable ETag)."""
        expected_plain = json.dumps({"version": "1", "automations": [], "user_actions": []})
        stub_state = mock.MagicMock()
        stub_state.to_json.return_value = expected_plain
        context = _make_context(identity="0xwallet", collection=enums.Collections.USER_DATA.value)
        with (
            mock.patch("octobot_sync.server.user_data_protocol") as mock_proto,
            mock.patch(
                "octobot_sync.server._get_wallet_private_key",
                return_value=_TEST_WALLET_PRIVATE_KEY,
            ),
        ):
            mock_proto.get_user_data_state = mock.AsyncMock(return_value=stub_state)
            first = json.loads(await server.get_data("users/0xwallet/data", context))
            second = json.loads(await server.get_data("users/0xwallet/data", context))
        assert first["hash"] == second["hash"]
        # AES-GCM nonce is random, so the encrypted payload must differ to prove
        # we are not just trivially returning the same ciphertext.
        assert first["data"] != second["data"]

    @pytest.mark.asyncio
    async def test_user_accounts_collection(self):
        """USER_ACCOUNTS returns the on-disk encrypted blob wrapped in a StoredDocument."""
        expected_plain = json.dumps({"version": "1", "accounts": []})
        encrypted_blob = sync_crypto.encrypt_bytes_to_blob_dict(
            expected_plain.encode("utf-8"),
            _TEST_WALLET_PRIVATE_KEY,
            enums.Collections.USER_ACCOUNTS.value,
        )
        encrypted_blob_json = json.dumps(encrypted_blob)
        context = _make_context(identity="0xwallet", collection=enums.Collections.USER_ACCOUNTS.value)
        with mock.patch("octobot_sync.server.accounts_protocol") as mock_proto:
            mock_proto.get_accounts_state_encrypted = mock.Mock(return_value=encrypted_blob)
            result = await server.get_data("users/0xwallet/accounts", context)
        mock_proto.get_accounts_state_encrypted.assert_called_once_with("0xwallet")
        wrapper = json.loads(result)
        assert wrapper["v"] == 1
        assert wrapper["timestamps"] == {}
        assert wrapper["hash"] == sync_crypto.sha256_hex(encrypted_blob_json)
        assert wrapper["data"] == encrypted_blob_json
        decrypted_plain = sync_crypto.decrypt_blob_dict_to_bytes(
            json.loads(wrapper["data"]),
            _TEST_WALLET_PRIVATE_KEY,
            enums.Collections.USER_ACCOUNTS.value,
        ).decode("utf-8")
        assert decrypted_plain == expected_plain

    @pytest.mark.asyncio
    async def test_user_accounts_auth_collection(self):
        expected_plain = json.dumps({"version": "1", "account_authentication": []})
        encrypted_blob = sync_crypto.encrypt_bytes_to_blob_dict(
            expected_plain.encode("utf-8"),
            _TEST_WALLET_PRIVATE_KEY,
            enums.Collections.USER_ACCOUNTS_AUTH.value,
        )
        encrypted_blob_json = json.dumps(encrypted_blob)
        context = _make_context(
            identity="0xwallet",
            collection=enums.Collections.USER_ACCOUNTS_AUTH.value,
        )
        with mock.patch("octobot_sync.server.accounts_auth_protocol") as mock_proto:
            mock_proto.get_accounts_authentication_state_encrypted = mock.Mock(
                return_value=encrypted_blob
            )
            result = await server.get_data("users/0xwallet/accounts/auth", context)
        mock_proto.get_accounts_authentication_state_encrypted.assert_called_once_with("0xwallet")
        wrapper = json.loads(result)
        assert wrapper["hash"] == sync_crypto.sha256_hex(encrypted_blob_json)
        assert wrapper["data"] == encrypted_blob_json

    @pytest.mark.asyncio
    async def test_USER_ACCOUNTS_TRADING_collection(self):
        expected_plain = json.dumps({"version": "1", "account_trading": []})
        encrypted_blob = sync_crypto.encrypt_bytes_to_blob_dict(
            expected_plain.encode("utf-8"),
            _TEST_WALLET_PRIVATE_KEY,
            enums.Collections.USER_ACCOUNTS_TRADING.value,
        )
        encrypted_blob_json = json.dumps(encrypted_blob)
        context = _make_context(
            identity="0xwallet",
            collection=enums.Collections.USER_ACCOUNTS_TRADING.value,
            params={"account_id": "acc-1"},
        )
        with mock.patch("octobot_sync.server.accounts_trading_protocol") as mock_proto:
            mock_proto.get_account_trading_state_encrypted = mock.Mock(
                return_value=encrypted_blob
            )
            result = await server.get_data("users/0xwallet/accounts/acc-1/trading", context)
        mock_proto.get_account_trading_state_encrypted.assert_called_once_with("0xwallet", "acc-1")
        wrapper = json.loads(result)
        assert wrapper["hash"] == sync_crypto.sha256_hex(encrypted_blob_json)
        assert wrapper["data"] == encrypted_blob_json

    @pytest.mark.asyncio
    async def test_unmatched_collection_reads_opaque_store(self):
        """Any collection without a protocol-bridge case falls through to
        opaque filesystem storage and the node never touches the ciphertext."""
        stored_ciphertext = "opaque-ciphertext-payload"
        mock_store = mock.MagicMock()
        mock_store.get_string = mock.AsyncMock(return_value=stored_ciphertext)
        context = _make_context(identity="0xwallet", collection="user-settings")
        with mock.patch("octobot_sync.server._get_opaque_store", return_value=mock_store):
            result = await server.get_data("users/0xwallet/settings", context)
        mock_store.get_string.assert_awaited_once_with("users/0xwallet/settings")
        wrapper = json.loads(result)
        assert wrapper["data"] == stored_ciphertext
        assert wrapper["hash"] == sync_crypto.sha256_hex(stored_ciphertext)

    @pytest.mark.asyncio
    async def test_unmatched_collection_returns_none_when_no_stored_value(self):
        mock_store = mock.MagicMock()
        mock_store.get_string = mock.AsyncMock(return_value=None)
        context = _make_context(identity="0xwallet", collection="user-strategies")
        with mock.patch("octobot_sync.server._get_opaque_store", return_value=mock_store):
            result = await server.get_data("users/0xwallet/strategies", context)
        assert result is None


class TestPutData:
    @pytest.mark.asyncio
    async def test_user_actions_executes_each_action(self):
        plain_body = json.dumps({
            "version": "1",
            "user_actions": [
                {"id": "act-1"},
                {"id": "act-2"},
            ],
        })
        encrypted = sync_crypto.encrypt_utf8_json_to_wire(
            plain_body,
            _TEST_WALLET_PRIVATE_KEY,
            enums.Collections.USER_ACTIONS.value,
        )
        body = json.dumps({"v": 1, "data": encrypted, "timestamps": {}, "hash": "x"})
        context = _make_context(identity="0xwallet", collection=enums.Collections.USER_ACTIONS.value)

        # Build real action stubs since protocol_models is mocked in conftest.
        action1 = mock.MagicMock()
        action1.id = "act-1"
        action2 = mock.MagicMock()
        action2.id = "act-2"
        fake_state = mock.MagicMock()
        fake_state.user_actions = [action1, action2]

        with (
            mock.patch("octobot_sync.server.user_actions_protocol") as mock_proto,
            mock.patch(
                "octobot_sync.server._get_wallet_private_key",
                return_value=_TEST_WALLET_PRIVATE_KEY,
            ),
            mock.patch("octobot_sync.server.protocol_models") as mock_pm,
        ):
            mock_pm.UserActionsState.from_json.return_value = fake_state
            mock_proto.execute_user_action = mock.AsyncMock()
            await server.put_data("users/0xwallet/actions", body, context)
        assert mock_proto.execute_user_action.await_count == 2
        calls = mock_proto.execute_user_action.await_args_list
        assert calls[0].args[0].id == "act-1"
        assert calls[0].args[1] == "0xwallet"
        assert calls[1].args[0].id == "act-2"
        assert calls[1].args[1] == "0xwallet"

    @pytest.mark.asyncio
    async def test_user_actions_logs_exception_on_failure(self):
        plain_body = json.dumps({
            "version": "1",
            "user_actions": [{"id": "fail-action"}],
        })
        encrypted = sync_crypto.encrypt_utf8_json_to_wire(
            plain_body,
            _TEST_WALLET_PRIVATE_KEY,
            enums.Collections.USER_ACTIONS.value,
        )
        body = json.dumps({"v": 1, "data": encrypted, "timestamps": {}, "hash": "x"})
        context = _make_context(identity="0xwallet", collection=enums.Collections.USER_ACTIONS.value)
        mock_logger = mock.MagicMock()

        fail_action = mock.MagicMock()
        fail_action.id = "fail-action"
        fake_state = mock.MagicMock()
        fake_state.user_actions = [fail_action]

        with (
            mock.patch("octobot_sync.server.user_actions_protocol") as mock_proto,
            mock.patch("octobot_sync.server._get_logger", return_value=mock_logger),
            mock.patch(
                "octobot_sync.server._get_wallet_private_key",
                return_value=_TEST_WALLET_PRIVATE_KEY,
            ),
            mock.patch("octobot_sync.server.protocol_models") as mock_pm,
        ):
            mock_pm.UserActionsState.from_json.return_value = fake_state
            mock_proto.execute_user_action = mock.AsyncMock(side_effect=RuntimeError("boom"))
            await server.put_data("users/0xwallet/actions", body, context)
        mock_logger.exception.assert_called_once()

    @pytest.mark.asyncio
    async def test_unmatched_collection_writes_to_opaque_store(self):
        """Any collection without a protocol-bridge case persists the unwrapped
        ciphertext as-is — server side never decrypts."""
        ciphertext = "opaque-ciphertext-payload"
        body = json.dumps({"v": 1, "data": ciphertext, "timestamps": {}, "hash": "x"})
        mock_store = mock.MagicMock()
        mock_store.put = mock.AsyncMock()
        context = _make_context(identity="0xwallet", collection="user-settings")
        with mock.patch("octobot_sync.server._get_opaque_store", return_value=mock_store):
            await server.put_data("users/0xwallet/settings", body, context)
        mock_store.put.assert_awaited_once_with(
            "users/0xwallet/settings", ciphertext, content_type="application/json"
        )


class TestStoredDocumentHelpers:
    def test_wrap_produces_stored_document_shape(self):
        wrapped = server._wrap_as_stored_document("encrypted-payload", "plaintext")
        parsed = json.loads(wrapped)
        assert parsed == {
            "v": 1,
            "data": "encrypted-payload",
            "timestamps": {},
            "hash": sync_crypto.sha256_hex("plaintext"),
        }

    def test_wrap_hash_is_plaintext_hash_not_ciphertext_hash(self):
        """Hash must derive from plaintext so it stays stable across pulls."""
        first = json.loads(server._wrap_as_stored_document("ciphertext-A", "plaintext"))
        second = json.loads(server._wrap_as_stored_document("ciphertext-B", "plaintext"))
        assert first["hash"] == second["hash"]
        assert first["data"] != second["data"]

    def test_unwrap_returns_data_field(self):
        body = json.dumps({"v": 1, "data": "encrypted", "timestamps": {}, "hash": "abc"})
        assert server._unwrap_stored_document_data(body) == "encrypted"

    def test_unwrap_raises_when_data_missing(self):
        body = json.dumps({"v": 1, "timestamps": {}, "hash": "abc"})
        with pytest.raises(errors.OctobotSyncError):
            server._unwrap_stored_document_data(body)

    def test_unwrap_raises_when_data_not_string(self):
        body = json.dumps({"v": 1, "data": {"nested": True}, "timestamps": {}, "hash": "abc"})
        with pytest.raises(errors.OctobotSyncError):
            server._unwrap_stored_document_data(body)


class TestSetDataCallbacks:
    def test_sets_module_globals(self):
        original_get = server._get_data
        original_put = server._put_data
        try:
            sentinel_get = mock.AsyncMock()
            sentinel_put = mock.AsyncMock()
            server.set_data_callbacks(sentinel_get, sentinel_put)
            assert server._get_data is sentinel_get
            assert server._put_data is sentinel_put
        finally:
            server._get_data = original_get
            server._put_data = original_put


class TestCallbackObjectStore:
    @pytest.mark.asyncio
    async def test_get_string_forwards_context(self):
        original_get = server._get_data
        original_put = server._put_data
        try:
            callback = mock.AsyncMock(return_value="payload")
            server._get_data = callback
            server._put_data = mock.AsyncMock()
            store = server._CallbackObjectStore()
            context = _make_context()
            result = await store.get_string("my-key", context=context)
            assert result == "payload"
            callback.assert_awaited_once_with("my-key", context)
        finally:
            server._get_data = original_get
            server._put_data = original_put

    @pytest.mark.asyncio
    async def test_put_forwards_context(self):
        original_get = server._get_data
        original_put = server._put_data
        try:
            callback = mock.AsyncMock()
            server._get_data = mock.AsyncMock()
            server._put_data = callback
            store = server._CallbackObjectStore()
            context = _make_context()
            await store.put("my-key", "body-text", context=context)
            callback.assert_awaited_once_with("my-key", "body-text", context)
        finally:
            server._get_data = original_get
            server._put_data = original_put

    @pytest.mark.asyncio
    async def test_list_keys_returns_empty(self):
        original_get = server._get_data
        original_put = server._put_data
        try:
            server._get_data = mock.AsyncMock()
            server._put_data = mock.AsyncMock()
            store = server._CallbackObjectStore()
            assert await store.list_keys("prefix") == []
        finally:
            server._get_data = original_get
            server._put_data = original_put

    @pytest.mark.asyncio
    async def test_delete_raises(self):
        original_get = server._get_data
        original_put = server._put_data
        try:
            server._get_data = mock.AsyncMock()
            server._put_data = mock.AsyncMock()
            store = server._CallbackObjectStore()
            with pytest.raises(NotImplementedError):
                await store.delete("key")
        finally:
            server._get_data = original_get
            server._put_data = original_put

    @pytest.mark.asyncio
    async def test_delete_many_raises(self):
        original_get = server._get_data
        original_put = server._put_data
        try:
            server._get_data = mock.AsyncMock()
            server._put_data = mock.AsyncMock()
            store = server._CallbackObjectStore()
            with pytest.raises(NotImplementedError):
                await store.delete_many(["k1", "k2"])
        finally:
            server._get_data = original_get
            server._put_data = original_put


class TestBuildObjectStore:
    def test_returns_callback_store_when_callbacks_set(self):
        original_get = server._get_data
        original_put = server._put_data
        try:
            server._get_data = mock.AsyncMock()
            server._put_data = mock.AsyncMock()
            store = server.build_object_store()
            assert isinstance(store, server._CallbackObjectStore)
        finally:
            server._get_data = original_get
            server._put_data = original_put

    def test_returns_s3_store_when_env_set(self):
        original_get = server._get_data
        original_put = server._put_data
        try:
            server._get_data = None
            server._put_data = None
            env = {
                "S3_ENDPOINT": "https://s3.example.com",
                "S3_ACCESS_KEY": "key",
                "S3_SECRET_KEY": "secret",
                "S3_BUCKET": "bucket",
                "S3_REGION": "us-east-1",
            }
            sentinel = mock.MagicMock(spec=S3ObjectStore)
            with (
                mock.patch.dict(os.environ, env, clear=False),
                mock.patch("octobot_sync.server.S3ObjectStore", return_value=sentinel),
            ):
                store = server.build_object_store()
            assert store is sentinel
        finally:
            server._get_data = original_get
            server._put_data = original_put

    def test_returns_filesystem_store_by_default(self):
        original_get = server._get_data
        original_put = server._put_data
        try:
            server._get_data = None
            server._put_data = None
            env_clear = {k: "" for k in ("S3_ENDPOINT",)}
            with mock.patch.dict(os.environ, env_clear, clear=False):
                os.environ.pop("S3_ENDPOINT", None)
                store = server.build_object_store()
            assert isinstance(store, FilesystemObjectStore)
        finally:
            server._get_data = original_get
            server._put_data = original_put


class TestBuildDefaultSyncApp:
    def test_returns_app(self):
        sentinel_app = mock.MagicMock()
        with (
            mock.patch("octobot_sync.server.build_object_store", return_value=mock.MagicMock()) as mock_build,
            mock.patch("octobot_sync.server.sync_app") as mock_sync_app,
        ):
            mock_sync_app.create_app.return_value = sentinel_app
            result = server.build_default_sync_app(
                is_allowed_user_id=None,
                sync_config=None,
            )
        assert result is sentinel_app
        mock_build.assert_called_once()
        mock_sync_app.create_app.assert_called_once()
        call_kwargs = mock_sync_app.create_app.call_args
        assert call_kwargs.kwargs["is_allowed_user_id"] is None
        assert call_kwargs.kwargs["sync_config"] is None
