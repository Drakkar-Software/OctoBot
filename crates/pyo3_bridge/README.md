# pyo3_bridge — Shared PyO3 Bridging Utilities

Reusable helpers for PyO3 bridge crates (`*_py`). Any utility that bridges
Python and Rust async runtimes and is not specific to a single domain crate
belongs here.

## Modules

```
src/
├── lib.rs             re-exports
├── async_methods.rs   await_py_method0, await_py_method1, for_each_await
├── event_loop.rs      try_get_event_loop
└── futures.rs         py_none_future
```

### `async_methods`

Helpers to call async Python methods from Rust futures:

| Function | Description |
|----------|-------------|
| `await_py_method0(obj, method)` | Acquire GIL, call a no-arg async method, await it |
| `await_py_method1(obj, method, arg)` | Same with one argument |
| `for_each_await(items, method)` | Call a no-arg async method on each item sequentially |

### `event_loop`

| Function | Description |
|----------|-------------|
| `try_get_event_loop(py)` | Try to get the running asyncio event loop. Returns `None` when called from a thread without an active loop (e.g. a tokio worker thread) |

### `futures`

| Function | Description |
|----------|-------------|
| `py_none_future(py)` | Return a Python awaitable that immediately resolves to `None` |

## Usage

Add to your `Cargo.toml`:

```toml
[dependencies]
pyo3_bridge = { path = "../pyo3_bridge" }
```

```rust
use pyo3_bridge::async_methods::await_py_method0;
use pyo3_bridge::event_loop::try_get_event_loop;
use pyo3_bridge::futures::py_none_future;
```

## Dependencies

```
pyo3_bridge  ─depends on→  pyo3 0.28
             ─depends on→  pyo3-async-runtimes 0.28
```
