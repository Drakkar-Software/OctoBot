# octobot_evaluators_py -- PyO3 Bridge

PyO3 bindings that expose the [`octobot_evaluators`](../octobot_evaluators/)
Rust library to Python as a drop-in replacement for
[packages/OctoBot-Evaluators](../../packages/OctoBot-Evaluators/).

## Golden rule

> **This crate contains ZERO business logic.**
> Every method is a thin wrapper that calls into `octobot_evaluators`.
> If you need to change behaviour, change the Rust crate.

## Architecture

```
src/
├── lib.rs                   #[pymodule] registration + constant/enum export
├── tree/
│   ├── mod.rs
│   ├── base_tree.rs         PyBaseTree, PyBaseTreeNode (T = Py<PyAny>)
│   └── base_tree_node.rs    PyBaseTreeNode standalone helpers
├── matrix/
│   ├── mod.rs
│   ├── matrix.rs            PyMatrix
│   ├── matrices.rs          PyMatrices
│   └── matrix_manager.rs    PyMatrixManager
└── channels/
    ├── mod.rs
    ├── evaluator_channel.rs   PyEvaluatorChannel (extends async_channel_py::PyChannel)
    ├── evaluators_channel.rs  PyEvaluatorsChannel (extends async_channel_py::PyChannel)
    └── matrix_channel.rs      PyMatrixChannel (extends async_channel_py::PyChannel)

python/
└── octobot_evaluators_rs/
    ├── __init__.py          from ._core import *
    └── _enums.py            Python-side enum definitions
```

### Tree nodes use `Py<PyAny>`

The generic `BaseTree<T>` / `BaseTreeNode<T>` from the core crate is
instantiated with `T = Py<PyAny>` in the bridge. This lets Python code store
arbitrary objects (floats, strings, class instances) as node values without
forcing conversion to a fixed Rust enum.

### Channel hierarchy

`PyEvaluatorChannel`, `PyEvaluatorsChannel`, and `PyMatrixChannel` extend the
`PyChannel` type from [`async_channel_py`](../async_channel_py/), adding
evaluator-specific fields and methods. The same `future_into_py` /
`into_future` async bridging pattern is used.

### Dependency graph

```
octobot_evaluators_py  ─depends on→  octobot_evaluators  (logic)
                       ─depends on→  async_channel        (channel base types)
                       ─depends on→  async_channel_py     (PyChannel base class)
                       ─depends on→  pyo3_bridge          (shared PyO3 helpers)
                       ─depends on→  pyo3 0.28            (bindings)
                       ─depends on→  pyo3-async-runtimes 0.28  (async bridge)
```

## Build

```bash
cd crates/octobot_evaluators_py
maturin develop          # debug (requires virtualenv)
maturin develop --release  # optimized (requires virtualenv)

# Without a virtualenv (e.g. in CI):
maturin build --release
pip install ../../target/wheels/octobot_evaluators_rs-*.whl
```

## Test

```bash
# Pure Rust tests (no Python needed)
cargo test -p octobot_evaluators

# Python backend (default)
cd packages/OctoBot-Evaluators && pytest tests/

# Rust backend
cd packages/OctoBot-Evaluators && pytest tests/ --backend=rust
```
