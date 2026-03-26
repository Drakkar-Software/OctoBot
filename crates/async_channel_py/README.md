# async_channel_py — PyO3 Bridge

PyO3 bindings that expose the [`async_channel`](../async_channel/) Rust library
to Python as a drop-in replacement for
[packages/async_channel](../../packages/async_channel/).

## Golden rule

> **This crate contains ZERO business logic.**
> Every method is a thin wrapper that calls into `async_channel`.
> If you need to change behaviour, change the Rust crate.
>
> **Exception**: `_filter_consumers` uses Python-native `eq()` comparison
> because Python's cross-type equality (`1 == True`) cannot be reproduced
> through string conversion. The algorithm mirrors core's `check_filters`
> but operates on Python objects directly.

### Private method convention

Python methods starting with `_` are **not bridged** to Python unless they are
called through `self.` in the original Python code (which means subclasses may
override them).

| Method | Bridged? | Reason |
|--------|----------|--------|
| `_should_pause_producers` | Yes | Called as `self._should_pause_producers()` (channel.py:217) |
| `_should_resume_producers` | Yes | Called as `self._should_resume_producers()` (channel.py:222) |
| `_filter_consumers` | Yes | Called as `self._filter_consumers()` — uses Python `eq()` for cross-type equality (e.g. `1 == True`); cannot delegate to core's string-based `check_filters` |
| `_check_producers_state` | Yes | Called as `self._check_producers_state()` (channel.py:115,210) |
| `_add_new_consumer_and_run` | Yes | Called as `self._add_new_consumer_and_run()` (channel.py:114) |
| `_check_filters` (module-level) | No | Called as `_check_filters(...)`, not via `self.` |
| `_instances` (classattr) | Yes | Required for singleton pattern |

When porting a new package, apply this rule: if a `_method` is called via
`self._method()` in the original Python code, it must be bridged (subclasses
may override it). If it's only called as a regular function or directly on the
class, keep it as a Rust-only method.

## Architecture

```
src/
├── lib.rs                   #[pymodule] registration + enum/constant export
├── consumer.rs              PyConsumer, PyInternalConsumer, PySupervisedConsumer
├── producer.rs              PyProducer
├── channels/
│   ├── mod.rs
│   ├── channel.rs           PyChannel + set_chan / get_chan / del_chan
│   └── channel_instances.rs PyChannelInstances + set_chan_at_id / …
└── util/
    ├── mod.rs
    ├── channel_creator.rs   create_channel_instance, create_all_subclasses_channel
    └── logging.rs           get_logger
```

Python bridging utilities (async method helpers, event loop caching, future
helpers) live in the shared [`pyo3_bridge`](../pyo3_bridge/) crate so they can
be reused by other `*_py` bridge crates.

```
python/
└── async_channel_rs/
    └── __init__.py          from ._core import *
```

### Dependency graph

```
async_channel_py  ─depends on→  async_channel   (logic)
                  ─depends on→  pyo3_bridge     (shared PyO3 helpers)
                  ─depends on→  pyo3 0.28       (bindings)
                  ─depends on→  pyo3-async-runtimes 0.28  (async bridge)
```

## How it works

### Sync methods

Sync methods directly read/write fields on the Rust struct via
`slf.borrow()` / `slf.borrow_mut()`, delegating logic to `async_channel`:

```rust
fn start<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
    slf.borrow_mut().inner.start();          // ← Rust logic
    slf.borrow_mut().should_stop = false;    // ← keep Python field in sync
    future_into_py(py, async { Ok(py.None()) })
}
```

### Async methods

Async methods use `pyo3_async_runtimes::tokio::future_into_py` to return a
Python coroutine backed by a Rust future:

```rust
fn consume<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
    let c: Py<PyAny> = slf.as_any().clone().unbind();
    future_into_py(py, async move {
        // Call the Rust consume_loop, providing closures that
        // bridge Python asyncio objects ↔ Rust futures
        inner.consume_loop(
            || async { /* await queue.get() via into_future */ },
            |data| async { /* await self.perform(data) */ },
            || { /* log cancellation */ },
            |e| { /* log error */ },
            || async { /* await self.consume_ends() */ },
        ).await;
        Ok(py.None())
    })
}
```

Key helpers from `pyo3_async_runtimes`:

| Helper | What it does |
|--------|-------------|
| `future_into_py(py, future)` | Wraps a Rust `Future` as a Python coroutine |
| `into_future(bound_coroutine)` | Wraps a Python coroutine as a Rust `Future` |

### Event loop caching

Objects created inside `future_into_py` closures run on a tokio thread where
no asyncio event loop is set as "current". To schedule asyncio tasks (e.g.
`ensure_future`) from these threads, each `PyConsumer` / `PyProducer` caches
a reference to the event loop at construction time using
`pyo3_bridge::event_loop::try_get_event_loop`:

```rust
pub event_loop: Option<Py<PyAny>>,  // cached in __init__ via try_get_event_loop()
```

When `create_task()` needs to schedule the consume coroutine, it uses the
cached loop reference and temporarily sets it as the current loop for the
thread:

```rust
let loop_obj = match &slf.borrow().event_loop {
    Some(l) => l.clone_ref(py),
    None => asyncio.call_method0("get_running_loop")?.unbind(),
};
asyncio.call_method1("set_event_loop", (loop_obj.bind(py),))?;
let task = asyncio.call_method1("ensure_future", (coro,))?;
```

`Channel.new_consumer()` injects the caller's event loop into consumers it
creates, ensuring they can schedule tasks even when constructed on a tokio
thread.

### `__setattr__` / `__delattr__` for mock compatibility

PyO3 classes with `#[pyo3(get, set)]` fields don't automatically support
`mock.patch.object()` because Python's mock sets attributes via `setattr`,
which PyO3 doesn't route to the instance `__dict__` by default. Each
`#[pyclass]` implements explicit routing:

```rust
fn __setattr__(slf: &Bound<'_, Self>, name: &str, value: &Bound<'_, PyAny>) -> PyResult<()> {
    match name {
        "callback" => { slf.borrow_mut().callback = Some(value.clone().unbind()); Ok(()) },
        // ... other Rust fields ...
        _ => { slf.as_any().getattr("__dict__")?.set_item(name, value)?; Ok(()) },
    }
}
```

Known Rust fields are routed to their struct members; everything else goes
to `__dict__`. This enables `mock.patch.object(consumer, 'perform', ...)` to
work transparently.

### Injection (no changes to existing Python code)

The `conftest.py` in `packages/async_channel/` injects the Rust module into
`sys.modules` so `import async_channel` transparently resolves to
`async_channel_rs`:

```python
# conftest.py  (--backend=rust)
import async_channel_rs
sys.modules["async_channel"] = async_channel_rs
sys.modules["async_channel.channels"] = async_channel_rs
# … etc for every submodule
```

Zero lines of the original Python package are modified.

## Build

```bash
cd crates/async_channel_py
maturin develop          # debug (requires virtualenv)
maturin develop --release  # optimized (requires virtualenv)

# Without a virtualenv (e.g. in CI):
maturin build --release
pip install ../../target/wheels/async_channel_rs-*.whl
```

## Test

```bash
# Python backend (default)
cd packages/async_channel && pytest tests/

# Rust backend
cd packages/async_channel && pytest tests/ --backend=rust

# Pure Rust tests (no Python needed)
cargo test -p async_channel
```

## How to reproduce for another package

Follow these steps to port a new `packages/<pkg>` to Rust:

### Step 1 — Create the pure Rust crate

```bash
mkdir -p crates/<pkg>/src/{channels,util}  # mirror package dirs
```

- Copy constants, enums, and data types verbatim.
- For each class: create a Rust struct with the **state fields** only
  (`should_stop`, `priority_level`, etc.).
- Implement **all sync methods** as regular Rust methods.
- Implement **async orchestration** as generic `async fn` that take closures
  for I/O. This is the key design decision: the Rust crate defines _what_
  happens (control flow, error handling, state transitions), while the caller
  decides _how_ (tokio channels vs asyncio.Queue).
- Write `#[test]` and `#[tokio::test]` for everything.

### Step 2 — Create the `*_py` bridge crate

```bash
mkdir -p crates/<pkg>_py/src/{channels,util}
mkdir -p crates/<pkg>_py/python/<pkg>_rs
```

- `Cargo.toml`: depend on `<pkg>` (path) + `pyo3_bridge` (path) + `pyo3` 0.28 + `pyo3-async-runtimes`.
- `pyproject.toml`: maturin config with `module-name = "<pkg>_rs._core"`.
- For each Rust struct: create a `#[pyclass]` with `#[pyo3(get, set)]` fields
  mirroring the Python class, plus an `inner: <RustType>` field.
- **Sync methods**: call `self.inner.<method>()`, sync the Python-visible
  field.
- **Async methods**: `future_into_py(py, async { inner.<method>(...).await })`,
  using `into_future()` to bridge any Python awaitables.
- Register all classes, functions, constants in `#[pymodule]`.
- **Never** put logic in this crate. If you catch yourself writing an `if`
  that isn't about type conversion, it belongs in the Rust crate.

### Step 3 — conftest.py injection

Create `packages/<pkg>/conftest.py`:

```python
def pytest_configure(config):
    if config.getoption("--backend") == "rust":
        import <pkg>_rs
        sys.modules["<pkg>"] = <pkg>_rs
        # map every submodule
```

### Step 4 — CI

Add three jobs to `.github/workflows/main.yml`:

```yaml
rust-lint:   cargo clippy -p <pkg>
rust-test:   cargo test -p <pkg>
rust-python-test:
  - maturin build --release && pip install (in crates/<pkg>_py)
  - pytest packages/<pkg>/tests --backend=rust
```

### Checklist

- [ ] `cargo test -p <pkg>` — all pure Rust tests pass
- [ ] `pytest --backend=python` — original tests still pass (no code changes)
- [ ] `pytest --backend=rust` — tests pass against Rust backend
- [ ] No logic in `*_py` — only struct defs, field accessors, and `future_into_py` calls
- [ ] Private methods (`_foo`) not called via `self._foo()` are NOT bridged

## Lessons learned

### Async timing differences

The tokio-asyncio bridge introduces scheduling differences compared to pure
Python asyncio. Each Python method call in the Rust consume loop goes through:

```
Python::attach → call_method → into_future (ensure_future) → tokio await
```

Each hop requires an event loop iteration **and** wall-clock time for the
tokio thread to acquire the GIL. Tests that rely on exact scheduling (e.g.
"after N `await` yields, this callback has been called") may need adjustment:

- **`wait_asyncio_next_cycle()`**: The test helper uses
  `asyncio.sleep(0.01)` in a loop instead of
  `asyncio.create_task(do_nothing())` — the latter doesn't give the tokio
  thread enough wall-clock time to acquire the GIL and process pending work.
- **`mock_was_called_once()`**: Polls with `asyncio.sleep(0.01)` until the
  mock registers a call, up to 100 iterations.
- **Avoid timing-dependent assertions**: If a test asserts that something
  has NOT happened yet after yielding, ensure the blocking condition is
  structural (e.g. waiting on an unset `asyncio.Event`) rather than relying
  on "not enough event loop iterations have passed."

### Filter matching uses Python `eq()`, not core's `check_filters`

`_filter_consumers` cannot delegate to the core crate's `check_filters`
(which operates on `HashMap<String, String>`) because Python's cross-type
equality semantics must be preserved. For example, `1 == True` and
`0 == False` in Python — stringifying loses this. The bridge implements
the same algorithm using Python `eq()` on the original objects.

### `mock.patch.object` requires `__setattr__`

PyO3 `#[pyclass]` with `dict` does not automatically route `setattr` calls
to `__dict__`. Without explicit `__setattr__` / `__delattr__` methods,
`mock.patch.object()` silently fails to replace methods on instances. See
the "mock compatibility" section above.
