files(
    name="octobot_connectors_py_sources",
    sources=["Cargo.toml", "pyproject.toml", "src/**/*.rs", "python/**/*.py"],
)

package_shell_command(
    name="octobot-connectors-rs",
    command="maturin build --release --out .",
    execution_dependencies=[
        ":octobot_connectors_py_sources",
        "packages/connectors/crates/octobot_connectors_core:octobot_connectors_core_sources",
        "//:cargo_workspace",
    ],
    tools=["maturin", "cargo", "rustc", "cc", "python3", "ar", "bash"],
    output_files=["*.whl"],
    output_path="",
    workdir="/",
    timeout=300,
    description="Build octobot-connectors-rs maturin wheel",
)
