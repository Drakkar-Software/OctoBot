import re

import httpx
import mock
import pytest
import pytest_asyncio
from fastapi import FastAPI

from starfish_sdk import StarfishClient
from starfish_server.config.schema import (
    SyncConfig,
    CollectionConfig,
    NamespaceConfig,
    AppendOnlyConfig,
)
from starfish_sharing import make_registry_role_enricher
from starfish_spaces.client import ClientOpts, DeviceKeys
from starfish_spaces.session import BuildSessionOpts, build_session

import octobot_copy.constants as copy_constants
import octobot_protocol.models as protocol_models
import octobot_sync.app as sync_app
import octobot_sync.artifacts as artifacts
import octobot_sync.constants as sync_constants

import octobot_flow.entities
import octobot_flow.errors
import octobot_flow.repositories.community.trading_signals_repository as trading_signals_repository


class _MemoryObjectStore:
    """Minimal in-memory AbstractObjectStore (every method takes *, context=None). Mirrors
    packages/sync/tests/test_integration_artifacts.py's fixture of the same shape."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get_string(self, key, *, context=None):
        return self._store.get(key)

    async def put(self, key, body, *, content_type=None, cache_control=None, context=None):
        self._store[key] = body

    async def list_keys(self, prefix, *, start_after=None, limit=None, context=None):
        keys = sorted(k for k in self._store if k.startswith(prefix))
        if start_after:
            keys = [k for k in keys if k > start_after]
        return keys[:limit] if limit else keys

    async def delete(self, key, *, context=None):
        self._store.pop(key, None)

    async def delete_many(self, keys, *, context=None):
        for k in keys:
            self._store.pop(k, None)


_DK_NAMESPACE = "dk"

# Same dk_spaces collection set as packages/sync/tests/test_integration_artifacts.py — kept
# separate (not cross-package imported) since this package's tests aren't on the same sys.path
# root as packages/sync's.
_DK_CONFIG = SyncConfig(
    version=1,
    collections=[],
    namespaces={
        _DK_NAMESPACE: NamespaceConfig(
            collections=[
                CollectionConfig(
                    name="spaceregistry",
                    storagePath="spaces/{spaceId}/_access",
                    readRoles=["space:member"],
                    writeRoles=["space:owner"],
                    encryption="none",
                    maxBodyBytes=131_072,
                ),
                CollectionConfig(
                    name="spacekeyring",
                    storagePath="spaces/{spaceId}/_keyring",
                    readRoles=["space:member"],
                    writeRoles=["space:owner"],
                    encryption="none",
                    maxBodyBytes=65_536,
                ),
                CollectionConfig(
                    name="artifact-events",
                    storagePath="spaces/{spaceId}/artifact/versions/{version}/events",
                    readRoles=["space:member"],
                    writeRoles=["space:owner"],
                    encryption="delegated",
                    appendOnly=AppendOnlyConfig(type="by_timestamp", requireAuthorSignature=True),
                    maxBodyBytes=sync_constants.MAX_BODY_SIZE_SIGNAL,
                ),
            ]
        ),
    },
)


def _make_dk_role_enricher(store: _MemoryObjectStore):
    return make_registry_role_enricher(
        store,
        id_param="spaceId",
        registry_path="spaces/{id}/_access",
        owner_role="space:owner",
        member_role="space:member",
        allow_tofu=True,
        id_pattern=re.compile(r"^[a-zA-Z0-9_-]+$"),
    )


# Well-known Anvil/Hardhat account #1 — public, safe to embed in tests.
_PRIV = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"


@pytest.fixture
def dk_app():
    store = _MemoryObjectStore()
    inner = sync_app.create_app(
        store, sync_config=_DK_CONFIG, role_enricher=_make_dk_role_enricher(store)
    )
    outer = FastAPI()
    outer.mount("/sync", inner)
    return outer


async def _build_session(dk_app):
    """A real starfish_spaces Session wired to the in-process dk_app via ASGITransport — same
    transport-monkeypatch pattern as packages/sync/tests/test_integration_artifacts.py."""
    transport = httpx.ASGITransport(app=dk_app)

    from octobot_sync.auth.provider import derive_root_identity
    import starfish_spaces.client as spaces_client_module
    import starfish_spaces.session as spaces_session_module

    root = derive_root_identity(_PRIV)
    keys: DeviceKeys = {
        "edPriv": root.keys.ed_priv,
        "edPub": root.keys.ed_pub,
        "kemPriv": root.keys.kem_priv,
        "kemPub": root.keys.kem_pub,
    }
    client_opts: ClientOpts = {"baseUrl": "http://test/sync", "namespace": _DK_NAMESPACE}

    def _make_space_client(cap, ed_priv_hex, opts):
        return StarfishClient(
            opts["baseUrl"],
            cap_provider=spaces_client_module.cap_provider_for(cap, ed_priv_hex),
            namespace=opts.get("namespace"),
            timeout=float(opts.get("timeout", 30.0)),
            client=httpx.AsyncClient(transport=transport),
        )

    original = spaces_session_module.make_space_client
    spaces_session_module.make_space_client = _make_space_client
    try:
        return await build_session(
            BuildSessionOpts(user_id=root.user_id, keys=keys, client_opts=client_opts)
        )
    finally:
        spaces_session_module.make_space_client = original


@pytest_asyncio.fixture
async def signal_session(dk_app):
    session = await _build_session(dk_app)
    yield session
    await session.content_client.close()
    await session.account_client.close()


@pytest.fixture
def repository(signal_session):
    """A TradingSignalsRepository whose _get_signal_session returns a real, in-process
    dk_spaces Session — so _upload_trading_signal/fetch_trading_signals exercise the real
    octobot_sync.artifacts calls, not a mock, matching the pattern already used for
    _upload_trading_signal in test_trading_signals_channel.py."""
    repo = trading_signals_repository.TradingSignalsRepository(mock.MagicMock())
    repo._get_signal_session = mock.AsyncMock(return_value=signal_session)
    return repo


def _trading_signal(strategy_id: str, updated_at: float) -> octobot_flow.entities.TradingSignal:
    return octobot_flow.entities.TradingSignal(
        strategy_id=strategy_id,
        account=protocol_models.CopiedAccount(
            version=copy_constants.COPIED_ACCOUNT_VERSION,
            updated_at=updated_at,
            copied_assets=[],
        ),
    )


class TestSignalSpaceId:
    def test_is_deterministic_for_the_same_strategy_id(self):
        assert trading_signals_repository._signal_space_id(
            "strat-a"
        ) == trading_signals_repository._signal_space_id("strat-a")

    def test_differs_across_strategy_ids(self):
        assert trading_signals_repository._signal_space_id(
            "strat-a"
        ) != trading_signals_repository._signal_space_id("strat-b")


class TestUploadAndFetchTradingSignal:
    @pytest.mark.asyncio
    async def test_upload_then_fetch_round_trips_a_trading_signal(self, repository):
        # The real gap this closes: _upload_trading_signal and _pull_trading_signals each
        # compute their own space_id via _signal_space_id(strategy_id) — nothing outside
        # this repository proves those two computations agree for the same strategy_id.
        signal = _trading_signal("strat-roundtrip", 1000.0)

        await repository._upload_trading_signal(signal)
        fetched = await repository.fetch_trading_signals(["strat-roundtrip"], history_size=10)

        assert len(fetched) == 1
        assert fetched[0].strategy_id == "strat-roundtrip"
        assert fetched[0].account.updated_at == 1000.0

    @pytest.mark.asyncio
    async def test_fetch_of_an_unpublished_strategy_returns_nothing(self, repository):
        fetched = await repository.fetch_trading_signals(["never-published"], history_size=10)
        assert fetched == []

    @pytest.mark.asyncio
    async def test_upload_trading_signal_swallows_publish_errors(self, repository):
        with mock.patch.object(
            artifacts, "publish_artifact_event", mock.AsyncMock(side_effect=RuntimeError("boom"))
        ):
            # Must not raise — insert_trading_signal's caller (e.g. an automation job) must
            # not crash because the sync server was unreachable.
            await repository._upload_trading_signal(_trading_signal("strat-x", 1.0))

    @pytest.mark.asyncio
    async def test_fetch_trading_signals_raises_for_a_failing_strategy_after_trying_the_rest(
        self, repository
    ):
        ok_signal = _trading_signal("strat-ok", 1000.0)
        await repository._upload_trading_signal(ok_signal)

        broken_space_id = trading_signals_repository._signal_space_id("strat-broken")
        real_pull = artifacts.pull_artifact_events
        attempted_space_ids = []

        async def _pull_that_fails_for_the_broken_space(session, space_id, version, last, **kwargs):
            attempted_space_ids.append(space_id)
            if space_id == broken_space_id:
                raise RuntimeError("boom")
            return await real_pull(session, space_id, version, last, **kwargs)

        with mock.patch.object(
            artifacts, "pull_artifact_events", _pull_that_fails_for_the_broken_space
        ):
            with pytest.raises(octobot_flow.errors.CommunityTradingSignalError, match="strat-broken"):
                await repository.fetch_trading_signals(
                    ["strat-broken", "strat-ok"], history_size=10
                )

        # Both strategies were attempted — the broken one didn't abort the loop early.
        ok_space_id = trading_signals_repository._signal_space_id("strat-ok")
        assert set(attempted_space_ids) == {broken_space_id, ok_space_id}

    @pytest.mark.asyncio
    async def test_fetch_trading_signals_reuses_a_single_session_across_strategies(self, repository):
        await repository._upload_trading_signal(_trading_signal("strat-a", 1.0))
        await repository._upload_trading_signal(_trading_signal("strat-b", 2.0))
        repository._get_signal_session.reset_mock()

        fetched = await repository.fetch_trading_signals(["strat-a", "strat-b"], history_size=10)

        assert {signal.strategy_id for signal in fetched} == {"strat-a", "strat-b"}
        repository._get_signal_session.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fetch_trading_signals_returns_the_most_recently_updated_signal(self, repository):
        strategy_id = "strat-newest-wins"
        await repository._upload_trading_signal(_trading_signal(strategy_id, 100.0))
        await repository._upload_trading_signal(_trading_signal(strategy_id, 200.0))

        fetched = await repository.fetch_trading_signals([strategy_id], history_size=10)

        assert len(fetched) == 1
        assert fetched[0].account.updated_at == 200.0

    @pytest.mark.asyncio
    async def test_fetch_trading_signals_trims_historical_snapshots_to_history_size(self, repository):
        strategy_id = "strat-trim"
        snapshots = [
            protocol_models.CopiedAccount(
                version=copy_constants.COPIED_ACCOUNT_VERSION,
                updated_at=float(index),
                copied_assets=[],
            )
            for index in range(5)
        ]
        signal = _trading_signal(strategy_id, 1000.0)
        signal.account.historical_snapshots = snapshots

        await repository._upload_trading_signal(signal)
        fetched = await repository.fetch_trading_signals([strategy_id], history_size=2)

        assert len(fetched) == 1
        assert len(fetched[0].account.historical_snapshots) == 2
