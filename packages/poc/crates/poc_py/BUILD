files(
    name="poc_py_sources",
    sources=["Cargo.toml", "pyproject.toml", "src/**/*.rs", "python/**/*.py"],
)

package_shell_command(
    name="octobot-poc-rs",
    command="maturin build --release --manifest-path packages/poc/crates/poc_py/Cargo.toml --out .",
    execution_dependencies=[
        ":poc_py_sources",
        "packages/poc/crates/poc_core:poc_core_sources",
        "//:cargo_workspace",
    ],
    tools=["maturin", "cargo", "rustc", "cc", "python3", "ar", "bash"],
    output_files=["*.whl"],
    output_path="",
    workdir="/",
    timeout=300,
    description="Build octobot-poc-rs maturin wheel",
)
