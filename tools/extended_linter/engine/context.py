import dataclasses
import pathlib
import typing

import tools.extended_linter.domain.models as domain_models


@dataclasses.dataclass
class RunContext:
    repo_root: pathlib.Path
    base_ref: str
    policy: dict[str, typing.Any]
    changed_paths: list[str] = dataclasses.field(default_factory=list)
    merge_base_sha: str = ""
    diff_text: str = ""
    violations: list[domain_models.Violation] = dataclasses.field(default_factory=list)
