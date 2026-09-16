import pathlib
import typing

import tools.extended_linter.config.loader as config_loader
import tools.extended_linter.domain.models as domain_models
import tools.extended_linter.engine.context as engine_context
import tools.extended_linter.hooks.tentacles as hooks_tentacles
import tools.extended_linter.layers.diff_policy as layer_diff
import tools.extended_linter.layers.git_scope as layer_git
import tools.extended_linter.layers.path_policy as layer_path


class RunnerConfig(typing.NamedTuple):
    repo_root: pathlib.Path
    base_ref: str
    policy_path: pathlib.Path | None
    skip_tentacles_reinstall: bool


def run(config: RunnerConfig) -> list[domain_models.Violation]:
    policy = config_loader.load_policy(config.policy_path)
    context = engine_context.RunContext(
        repo_root=config.repo_root,
        base_ref=config.base_ref,
        policy=policy,
    )
    context.violations.extend(
        layer_git.verify_merge_base(context.repo_root, context.base_ref, context.policy)
    )
    if context.violations:
        return context.violations
    context.changed_paths, context.merge_base_sha = layer_git.list_changed_paths(
        context.repo_root,
        context.base_ref,
    )
    if (
        not config.skip_tentacles_reinstall
        and hooks_tentacles.diff_touches_tentacles_sources(context.changed_paths)
    ):
        hooks_tentacles.run_reinstall(context.repo_root)
    context.violations.extend(layer_path.run(context.changed_paths, context.policy))
    context.diff_text = layer_git.unified_diff(context.repo_root, context.merge_base_sha)
    context.violations.extend(layer_diff.run(context.diff_text, context.policy))
    return context.violations
