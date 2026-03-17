# from https://www.pantsbuild.org/stable/docs/writing-plugins/common-plugin-tasks/custom-python-artifact-kwargs


from __future__ import annotations

import os.path

from pants.backend.python.util_rules.package_dists import SetupKwargs, SetupKwargsRequest
from pants.engine.target import Target
from pants.engine.fs import DigestContents, GlobMatchErrorBehavior, PathGlobs
from pants.engine.intrinsics import get_digest_contents
from pants.engine.unions import UnionRule
from pants.engine.rules import collect_rules, goal_rule, implicitly, rule


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


def rules():
    return (*collect_rules(), UnionRule(SetupKwargsRequest, PantsSetupKwargsRequest))
