# octobot_evaluators -- Pure Rust Evaluator Library

Pure Rust implementation of the evaluator matrix, tree, and channel system
mirroring [packages/OctoBot-Evaluators](../../packages/OctoBot-Evaluators/).

## Purpose

This crate provides the **data structures and logic** for the OctoBot evaluator
system: a matrix that stores evaluator outputs in a tree structure, plus
dedicated channels for evaluator and matrix communication. It has **zero Python
dependency** and compiles as a standalone Rust library with its own test suite.

The companion crate [`octobot_evaluators_py`](../octobot_evaluators_py/) wraps
every type exposed here with PyO3 so Python code can use the exact same
implementation.

## Architecture

```
src/
├── lib.rs              re-exports
├── constants.rs        evaluator config keys and channel names
├── enums.rs            EvaluatorMatrixTypes, MatrixValueType
├── errors.rs           NodeExistsError
├── tree/
│   ├── mod.rs
│   ├── base_tree.rs    BaseTree<T>, BaseTreeNode<T> (generic over value type)
│   └── node_value.rs   NodeValue enum (Float/Int/Str/Bool/None), NodeType, NodeMetadata
├── matrix/
│   ├── mod.rs
│   ├── matrix.rs       Matrix (wraps BaseTree<NodeValue>)
│   ├── matrices.rs     Matrices (collection of Matrix instances)
│   └── matrix_manager.rs  MatrixManager (evaluator registration, value get/set/update)
└── channels/
    ├── mod.rs
    ├── evaluator_channel.rs  EvaluatorChannel (extends async_channel::Channel)
    ├── evaluators.rs         EvaluatorsChannel (extends async_channel::Channel)
    └── matrix_channel.rs     MatrixChannel (extends async_channel::Channel)

tests/
├── test_matrix.rs      Matrix, Matrices, MatrixManager
└── test_tree.rs        BaseTree, BaseTreeNode, NodeValue
```

## Key design decisions

### Generic tree

`BaseTree<T>` and `BaseTreeNode<T>` are generic over the value type `T`:

- In the pure Rust crate, `T` is `NodeValue` -- a simple enum covering
  `Float(f64)`, `Int(i64)`, `Str(String)`, `Bool(bool)`, and `None`.
- In the PyO3 bridge, `T` is `Py<PyAny>` so tree nodes can hold arbitrary
  Python objects without conversion.

This avoids duplicating tree logic across the two crates.

### Channel hierarchy

The channel types (`EvaluatorChannel`, `EvaluatorsChannel`, `MatrixChannel`)
build on top of `async_channel::Channel`, extending it with evaluator-specific
fields and behaviour. The same callback-based async pattern from
[`async_channel`](../async_channel/) is used here.

## Running tests

```bash
cargo test -p octobot_evaluators
```

## Dependencies

```
octobot_evaluators  ─depends on→  async_channel  (channel base types)
                    ─depends on→  tokio          (async runtime, sync primitives)
                    ─depends on→  uuid           (node/matrix IDs)
```
