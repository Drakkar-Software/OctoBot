# from https://www.pantsbuild.org/stable/docs/writing-plugins/common-plugin-tasks/custom-python-artifact-kwargs


from __future__ import annotations

import os.path
import subprocess
import sys

from pants.backend.python.target_types import PythonRequirementsField
from pants.backend.python.util_rules.package_dists import SetupKwargs, SetupKwargsRequest
from pants.engine.console import Console
from pants.engine.fs import DigestContents, GlobMatchErrorBehavior, PathGlobs
from pants.engine.goal import Goal, GoalSubsystem
from pants.engine.intrinsics import get_digest_contents
from pants.engine.rules import collect_rules, goal_rule, implicitly, rule
from pants.engine.target import AllTargets, Target
from pants.engine.unions import UnionRule


class PantsSetupKwargsRequest(SetupKwargsRequest):
    @classmethod
    def is_applicable(cls, _: Target) -> bool:
        return True

@rule
async def setup_kwargs_plugin(request: PantsSetupKwargsRequest) -> SetupKwargs:
    original_kwargs = request.explicit_kwargs.copy()
    long_description_relpath = original_kwargs.pop("long_description_file", None)
    if not long_description_relpath:
        raise ValueError(
            f"The python_distribution target {request.target.address} did not include "
            "`long_description_file` in its python_artifact's kwargs. Our plugin requires this! "
            "Please set to a path relative to the BUILD file, e.g. `README.md`."
        )

    build_file_path = request.target.address.spec_path
    long_description_path = os.path.join(build_file_path, long_description_relpath)
    digest_contents = await get_digest_contents(
        **implicitly(PathGlobs(
            [long_description_path],
            description_of_origin=f"the 'long_description_file' kwarg in {request.target.address}",
            glob_match_error_behavior=GlobMatchErrorBehavior.error,
        ))
    )
    description_content = digest_contents[0].content.decode()
    return SetupKwargs(
        {**original_kwargs, "long_description": description_content},
        address=request.target.address
    )


class InstallDepsSubsystem(GoalSubsystem):
    name = "install-deps"
    help = "Install third-party Python dependencies into the local Python environment."

    @classmethod
    def register_options(cls, register) -> None:
        super().register_options(register)
        register(
            "--full",
            type=bool,
            default=False,
            help="Also install packages from full_requirements.txt files.",
        )


class InstallDeps(Goal):
    subsystem_cls = InstallDepsSubsystem
    environment_behavior = Goal.EnvironmentBehavior.LOCAL_ONLY


@goal_rule
async def install_deps(
    console: Console,
    targets: AllTargets,
    subsystem: InstallDepsSubsystem,
) -> InstallDeps:
    include_full = subsystem.options.full
    requirements: set[str] = set()
    for target in targets:
        if not target.has_field(PythonRequirementsField):
            continue
        if not include_full and target.address.target_name == "full_reqs":
            continue
        for req in target[PythonRequirementsField].value:
            requirements.add(str(req))

    if not requirements:
        console.print_stdout("No third-party requirements found.")
        return InstallDeps(exit_code=0)

    sorted_reqs = sorted(requirements)
    console.print_stdout(f"Installing {len(sorted_reqs)} packages into {sys.executable}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", *sorted_reqs],
        check=False,
    )
    return InstallDeps(exit_code=result.returncode)


def rules():
    return (*collect_rules(), UnionRule(SetupKwargsRequest, PantsSetupKwargsRequest))
