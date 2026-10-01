import pathlib
import subprocess
import typing

import tools.extended_linter.domain.models as domain_models
import tools.extended_linter.domain.paths as domain_paths


def verify_merge_base(
    repo_root: pathlib.Path,
    base_ref: str,
    policy: dict[str, typing.Any],
) -> list[domain_models.Violation]:
    violations: list[domain_models.Violation] = []
    git_rules = policy.get("git_rules") or []
    hint = "Fetch origin / fix branch name"
    for rule in git_rules:
        if rule.get("rule_id") == "git.merge_base_missing":
            hint = rule.get("hint", hint)
            break
    result = subprocess.run(
        ["git", "rev-parse", "--verify", base_ref],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        violations.append(
            domain_models.Violation(
                rule_id="git.merge_base_missing",
                file="",
                line=None,
                hint=hint,
                detail=result.stderr.strip() or f"unknown ref {base_ref}",
            )
        )
    return violations


def list_changed_paths(
    repo_root: pathlib.Path,
    base_ref: str,
) -> tuple[list[str], str]:
    merge_base = subprocess.run(
        ["git", "merge-base", "HEAD", base_ref],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if merge_base.returncode != 0:
        return [], merge_base.stderr.strip()
    merge_base_sha = merge_base.stdout.strip()
    name_only = subprocess.run(
        ["git", "diff", "--name-only", f"{merge_base_sha}...HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    paths = [
        domain_paths.normalize_path(line)
        for line in name_only.stdout.splitlines()
        if line.strip()
    ]
    return paths, merge_base_sha


def unified_diff(
    repo_root: pathlib.Path,
    merge_base_sha: str,
) -> str:
    diff_result = subprocess.run(
        ["git", "diff", f"{merge_base_sha}...HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return diff_result.stdout
