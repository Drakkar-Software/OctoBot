import pathlib
import subprocess

import tools.extended_linter.domain.paths as domain_paths

TENTACLES_SOURCE_PREFIX = "packages/tentacles/"


def diff_touches_tentacles_sources(changed_paths: list[str]) -> bool:
    for path in changed_paths:
        normalized = domain_paths.normalize_path(path)
        if normalized.startswith(TENTACLES_SOURCE_PREFIX):
            return True
    return False


def run_reinstall(repo_root: pathlib.Path) -> None:
    script = repo_root / ".cursor" / "reinstall-tentacles.sh"
    if not script.is_file():
        raise FileNotFoundError(f"missing tentacles reinstall script: {script}")
    subprocess.run(
        ["bash", str(script)],
        cwd=repo_root,
        check=True,
    )
