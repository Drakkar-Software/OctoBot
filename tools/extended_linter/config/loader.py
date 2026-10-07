import pathlib
import typing

import yaml


class PolicyLoadError(Exception):
    pass


def default_policy_path() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent / "policy.yaml"


def load_policy(policy_path: pathlib.Path | None = None) -> dict[str, typing.Any]:
    path = policy_path or default_policy_path()
    if not path.is_file():
        raise PolicyLoadError(f"policy file not found: {path}")
    with path.open(encoding="utf-8") as policy_file:
        data = yaml.safe_load(policy_file)
    if not isinstance(data, dict):
        raise PolicyLoadError("policy root must be a mapping")
    if data.get("policy_version") != 1:
        raise PolicyLoadError("unsupported policy_version")
    return data
