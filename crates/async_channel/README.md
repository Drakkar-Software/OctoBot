# async_channel — Pure Rust Channel Library

Pure Rust implementation of the producer-consumer channel pattern mirroring
[packages/async_channel](../../packages/async_channel/).

## Purpose

This crate provides the **logic and data structures** used by the OctoBot
async-channel system. It has **zero Python dependency** — it compiles and runs
as a standalone Rust library with its own test suite.

The companion crate [`async_channel_py`](../async_channel_py/) wraps every
function exposed here with PyO3 so Python code can use the exact same
implementation.

## Architecture

```
src/
├── lib.rs              re-exports
├── constants.rs        CHANNEL_WILDCARD, DEFAULT_QUEUE_SIZE
├── enums.rs            ChannelConsumerPriorityLevels (High / Medium / Optional)
├── consumer.rs         Consumer, ConsumeError, SupervisedState
├── producer.rs         Producer, SyncConsumerHandle, drain_queue
├── channels/
│   ├── mod.rs
│   ├── channel.rs      Channel, ConsumerEntry, FilterValue, check_filters
│   └── channel_instances.rs  ChannelInstances (singleton)
└── util/
    ├── mod.rs
    ├── channel_creator.rs  create_channel_instance, create_all_subclasses_channel
    └── logging.rs          get_logger_name

tests/
├── test_channel.rs           Channel, filters, pause/resume (mirrors test_channel.py)
├── test_consumer.rs          Consumer, SupervisedState, consume_loop (mirrors test_consumer.py)
├── test_producer.rs          Producer lifecycle, orchestration (mirrors test_producer.py)
├── test_synchronized.rs      drain_queue, synchronized_perform (mirrors test_synchronized.py)
├── test_channel_creator.rs   create_channel_instance (mirrors test_channel_creator.py)
├── test_channel_instances.rs ChannelInstances, ID channels (mirrors test_channel_instances.py)
└── test_logging.rs           get_logger_name, get_logger
```

The directory layout **mirrors** the Python package:

| Python module               | Rust module                          |
|-----------------------------|--------------------------------------|
| `async_channel.constants`   | `async_channel::constants`           |
| `async_channel.enums`       | `async_channel::enums`               |
| `async_channel.consumer`    | `async_channel::consumer`            |
| `async_channel.producer`    | `async_channel::producer`            |
| `async_channel.channels`    | `async_channel::channels`            |
| `async_channel.util`        | `async_channel::util`                |

## Design choices

### Callback-based async orchestration

Python's `asyncio.Queue`, `asyncio.Task` and `asyncio.Event` cannot be used
from pure Rust. Instead of hard-wiring a specific async runtime, each async
method accepts **closures** for the I/O operations:

```rust
consumer.consume_loop(
    get_data,       // async || → Result<T, ConsumeError>
    perform,        // async |T| → Result<(), ConsumeError>
    on_cancelled,   // || (sync callback)
    on_error,       // |E| (sync callback)
    consume_ends,   // async || → ()
).await;
```

This keeps the **control-flow logic** (the while loop, error classification,
finally semantics) in Rust while the caller decides _how_ to get/put data.

The PyO3 bridge provides closures that call `asyncio.Queue.get()`,
`asyncio.Queue.put()`, etc. through `pyo3_async_runtimes::tokio::into_future`.

### Queue draining

`Producer::drain_queue` is a generic async helper that repeatedly checks a
queue for emptiness, gets the next item, and calls a perform closure on it.
This keeps the drain algorithm in the core crate while the PyO3 bridge only
provides closures for the Python-specific queue operations.

### Stateless vs stateful

`Consumer` and `Producer` are lightweight state bags (`should_stop`,
`priority_level`, `is_running`). They own no queue or task handle because those
concepts are runtime-specific (tokio channels in Rust, asyncio.Queue in
Python).

`Channel` manages a `Vec<ConsumerEntry>` and producer count, plus
pause/resume logic.

### No `#[async_trait]`

All async functions use generic `impl FnMut() -> impl Future` bounds instead
of trait objects. This avoids the `async_trait` crate and keeps everything
zero-cost.

### Private method convention

Python methods starting with `_` (like `_should_pause_producers`) are
convention-private. In the Rust crate, these are regular public methods without
the underscore prefix (e.g. `should_pause_producers`). The `_` prefix is a
Python convention that has no meaning in Rust.

## Async timing considerations

The `consume_loop` method calls `consume_ends()` after every successful
`perform()` cycle, after cancellation errors, and after other errors. When
bridged to Python via PyO3, each of these calls goes through the
tokio-asyncio bridge (`future_into_py` / `into_future`), which means each
step requires a separate event loop iteration. See
[`async_channel_py/README.md`](../async_channel_py/README.md) for details on
how this affects test timing.

## Running tests

Tests live in the `tests/` directory (integration-style) mirroring the Python
test file layout from `packages/async_channel/tests/`. Source files contain no
inline `#[cfg(test)]` blocks.

```bash
cargo test -p async_channel
```

## How to reproduce for another package

1. **Identify the public API** of the Python package — every class, method,
   constant, and enum.
2. **Separate logic from I/O**: the Python code mixes both. Put the _logic_
   (state management, filtering, orchestration flow) into Rust structs and
   functions. Accept closures for anything that touches an async runtime or
   Python-specific type.
3. **Mirror the directory structure** so developers can navigate both codebases
   intuitively.
4. **Write Rust unit tests** for all sync functions and for async orchestration
   using `#[tokio::test]` with mock closures.
5. **Create the `*_py` crate** with only bridge code — see
   [`async_channel_py/README.md`](../async_channel_py/README.md).
