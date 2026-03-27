# OctoBot Packages

OctoBot is organized into self-contained packages under `packages/`. Each package encapsulates a specific domain and can contain Python code, Rust code, or both.

## Package Types

### Python Package

A standard Python package managed by Pants. This is the most common type.

```
packages/mypackage/
  mypackage/
    __init__.py
    module.py
  tests/
    test_module.py
  BUILD
  requirements.txt          # optional
  full_requirements.txt     # optional
```

**BUILD file:**
```python
python_sources(name="mypackage", sources=["mypackage/**/*.py"])

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[":mypackage", "//:dev_reqs"],
)
```

**Registration** (root `BUILD`):
- Add the package to `PACKAGE_SOURCES`
- Add its requirements to `PACKAGE_REQS` / `PACKAGE_FULL_REQS` if applicable

**Registration** (`pants.toml`):
- Add the package to `root_patterns` under `[source]`

**Registration** (`.github/workflows/main.yml`):
- Add the package to the test matrix

### Rust + Python Package

A package that contains both Python code and colocated Rust crates compiled via [PyO3](https://pyo3.rs/) and [maturin](https://www.maturin.rs/). The Rust code is exposed to Python as a compiled extension module.

```
packages/mypackage/
  mypackage/
    __init__.py
    core.py                           # imports from mypackage_rs
  tests/
    test_core.py
  crates/
    mypackage_core/                   # pure Rust library crate
      Cargo.toml
      src/
        lib.rs
    mypackage_py/                     # PyO3 bridge crate
      Cargo.toml
      pyproject.toml                  # maturin build config
      src/
        lib.rs
      python/
        mypackage_rs/                 # Python stub package
          __init__.py                 # re-exports from _core
      BUILD                           # Pants package_shell_command
  crates/
    mypackage_core/
      BUILD                           # files target for Rust sources
  BUILD
  standard.rc                         # pylint config with extension-pkg-whitelist
  requirements.txt
```

#### Rust Crate Layout

- **`mypackage_core/`**: Pure Rust library with the actual logic. No Python dependencies. Testable with `cargo test`.
- **`mypackage_py/`**: PyO3 bridge that wraps `mypackage_core` functions as Python-callable. Built by maturin into a wheel (`mypackage_rs`).

#### Cargo Configuration

The root `Cargo.toml` defines a workspace that auto-discovers all crates:

```toml
[workspace]
members = ["packages/*/crates/*"]
resolver = "2"
```

Each bridge crate has a `pyproject.toml` for maturin:

```toml
[build-system]
requires = ["maturin>=1.7,<2.0"]
build-backend = "maturin"

[project]
name = "mypackage-rs"
version = "0.1.0"
requires-python = ">=3.12"

[tool.maturin]
features = ["pyo3/extension-module"]
bindings = "pyo3"
module-name = "mypackage_rs._core"
python-source = "python"
```

#### Pants BUILD Files

**`crates/mypackage_core/BUILD`** - exposes Rust sources to the sandbox:
```python
files(
    name="mypackage_core_sources",
    sources=["Cargo.toml", "src/**/*.rs"],
)
```

**`crates/mypackage_py/BUILD`** - builds the Rust wheel via maturin:
```python
files(
    name="mypackage_py_sources",
    sources=["Cargo.toml", "pyproject.toml", "src/**/*.rs", "python/**/*.py"],
)

package_shell_command(
    name="mypackage-rs",
    command="maturin build --release --out .",
    execution_dependencies=[
        ":mypackage_py_sources",
        "packages/mypackage/crates/mypackage_core:mypackage_core_sources",
        "//:cargo_workspace",
    ],
    tools=["maturin", "cargo", "rustc", "cc", "python3", "ar", "bash"],
    output_files=["*.whl"],
    output_path="",
    workdir="/",
    timeout=300,
    description="Build mypackage-rs maturin wheel",
)
```

Key fields:
- `workdir="/"` sets the working directory to the sandbox root so the Cargo workspace resolves correctly
- `output_path=""` places the wheel at `dist/` root alongside the OctoBot wheel
- `execution_dependencies` brings Rust sources and the root `Cargo.toml`/`Cargo.lock` into the sandbox

#### Pylint Configuration

Create a `standard.rc` in the package directory to whitelist the compiled extension:

```ini
[MASTER]
extension-pkg-whitelist=mypackage_rs
fail-under=10.0
ignore=CVS,tests,additional_tests
```

#### CI Registration

In `.github/workflows/main.yml`:

1. **Build job** - Rust wheels are auto-discovered. The CI runs:
   ```yaml
   pants package :OctoBot $(pants list --filter-target-type=package_shell_command ::)
   ```
   Any `package_shell_command` target in the repo is automatically included. No manual registration needed.

2. **Test matrix** - the package is automatically detected as Rust-enabled via the `HAS_RUST` env var (uses `hashFiles` on `crates/**/Cargo.toml`), which triggers Rust linting and backend tests.

