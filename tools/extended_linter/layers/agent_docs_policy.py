import datetime
import pathlib
import re
import subprocess
import typing

import tools.extended_linter.domain.models as domain_models
import tools.extended_linter.domain.paths as domain_paths
import tools.extended_linter.layers.path_policy as layer_path_policy

_LAST_REVIEWED_SECTION = re.compile(
    r"##\s+Last reviewed\s*\n(?:.*\n)*?-\s*(\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)

_DEFAULT_PATH_GLOBS = [
    "**/AGENTS.md",
    ".cursor/skills/**/SKILL.md",
    ".cursor/README.md",
    ".cursor/rules/**",
    "CONTRIBUTING-agent.md",
    "tools/**/README.md",
    "tools/**/ARCHITECTURE.md",
]


def parse_last_reviewed_date(content: str) -> datetime.date | None:
    match = _LAST_REVIEWED_SECTION.search(content)
    if not match:
        return None
    try:
        return datetime.date.fromisoformat(match.group(1))
    except ValueError:
        return None


def should_flag_shrink(
    base_line_count: int,
    head_line_count: int,
    shrink_line_threshold: int,
) -> bool:
    return head_line_count < base_line_count - shrink_line_threshold


def matches_agent_doc_path(path: str, path_globs: list[str]) -> bool:
    normalized = domain_paths.normalize_path(path)
    for pattern in path_globs:
        if layer_path_policy._matches_glob(normalized, pattern):
            return True
    return False


def regression_reasons(
    base_content: str,
    head_content: str,
    shrink_line_threshold: int,
    doc_path: str = "agent doc",
) -> list[str]:
    reasons: list[str] = []
    base_lines = base_content.splitlines()
    head_lines = head_content.splitlines()
    if should_flag_shrink(len(base_lines), len(head_lines), shrink_line_threshold):
        reasons.append(
            f"Agent doc `{doc_path}` shrank by {len(base_lines) - len(head_lines)} lines "
            f"(threshold {shrink_line_threshold})"
        )
    base_reviewed = parse_last_reviewed_date(base_content)
    head_reviewed = parse_last_reviewed_date(head_content)
    if base_reviewed is not None and head_reviewed is not None:
        if head_reviewed < base_reviewed:
            reasons.append(
                f"Last reviewed regressed ({head_reviewed.isoformat()} "
                f"< {base_reviewed.isoformat()})"
            )
    return reasons


def _git_show_blob(
    repo_root: pathlib.Path,
    object_ref: str,
    path: str,
) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{object_ref}:{path}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _rule_config(
    policy: dict[str, typing.Any],
) -> tuple[str, str, int, list[str]]:
    rules = policy.get("agent_docs_rules") or []
    if not rules:
        return (
            "agent_docs.no_regression_vs_merge_base",
            "Do not shrink or backdate agent docs",
            5,
            list(_DEFAULT_PATH_GLOBS),
        )
    rule = rules[0]
    globs = rule.get("path_globs") or list(_DEFAULT_PATH_GLOBS)
    return (
        rule.get("rule_id", "agent_docs.no_regression_vs_merge_base"),
        rule.get(
            "hint",
            "Do not shrink or backdate agent docs unless this PR owns them; "
            "restore from origin/<base> or merge-base",
        ),
        int(rule.get("shrink_line_threshold", 5)),
        list(globs),
    )


def run(
    repo_root: pathlib.Path,
    merge_base_sha: str,
    changed_paths: list[str],
    policy: dict[str, typing.Any],
) -> list[domain_models.Violation]:
    rule_id, hint, shrink_threshold, path_globs = _rule_config(policy)
    violations: list[domain_models.Violation] = []
    for path in changed_paths:
        if not matches_agent_doc_path(path, path_globs):
            continue
        normalized = domain_paths.normalize_path(path)
        base_content = _git_show_blob(repo_root, merge_base_sha, normalized)
        if base_content is None:
            continue
        head_path = repo_root / normalized
        if not head_path.is_file():
            continue
        head_content = head_path.read_text(encoding="utf-8")
        for reason in regression_reasons(
            base_content,
            head_content,
            shrink_threshold,
            doc_path=normalized,
        ):
            violations.append(
                domain_models.Violation(
                    rule_id=rule_id,
                    file=normalized,
                    line=None,
                    hint=hint,
                    detail=reason,
                )
            )
    return violations
