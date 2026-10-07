import fnmatch
import typing

import tools.extended_linter.domain.models as domain_models
import tools.extended_linter.domain.paths as domain_paths


def _matches_glob(path: str, pattern: str) -> bool:
    normalized = domain_paths.normalize_path(path)
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return True
    if "/" not in pattern and "*" not in pattern:
        return normalized == pattern
    return fnmatch.fnmatch(normalized, pattern)


def _is_repo_root_tentacles(path: str) -> bool:
    normalized = domain_paths.normalize_path(path)
    if normalized.startswith("packages/tentacles/"):
        return False
    return normalized == "tentacles" or normalized.startswith("tentacles/")


def run(
    changed_paths: list[str],
    policy: dict[str, typing.Any],
) -> list[domain_models.Violation]:
    violations: list[domain_models.Violation] = []
    for rule in policy.get("path_rules") or []:
        rule_id = rule.get("rule_id", "")
        hint = rule.get("hint", "")
        kind = rule.get("kind")
        globs = rule.get("globs") or []
        for path in changed_paths:
            matched = False
            if kind == "repo_root_tentacles":
                matched = _is_repo_root_tentacles(path)
            else:
                for pattern in globs:
                    if _matches_glob(path, pattern):
                        matched = True
                        break
            if matched:
                violations.append(
                    domain_models.Violation(
                        rule_id=rule_id,
                        file=path,
                        line=None,
                        hint=hint,
                    )
                )
    return violations
