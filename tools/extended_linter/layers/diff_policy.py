import re
import typing

import tools.extended_linter.domain.models as domain_models


def _iter_added_lines(diff_text: str) -> list[tuple[str, int, str]]:
    current_file = ""
    line_number = 0
    added: list[tuple[str, int, str]] = []
    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ "):
            current_file = raw_line[4:].strip()
            if current_file.startswith("b/"):
                current_file = current_file[2:]
            continue
        if raw_line.startswith("@@"):
            hunk_match = re.search(r"\+(\d+)", raw_line)
            line_number = int(hunk_match.group(1)) if hunk_match else 0
            continue
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            added.append((current_file, line_number, raw_line[1:]))
            line_number += 1
        elif raw_line.startswith(" ") or raw_line.startswith("-"):
            if raw_line.startswith(" "):
                line_number += 1
    return added


def _subprocess_package_manager_line(line: str) -> bool:
    if "subprocess" not in line:
        return False
    lowered = line.lower()
    return "pip" in lowered or "npm install" in lowered


def run(
    diff_text: str,
    policy: dict[str, typing.Any],
) -> list[domain_models.Violation]:
    violations: list[domain_models.Violation] = []
    added_lines = _iter_added_lines(diff_text)
    for rule in policy.get("diff_rules") or []:
        rule_id = rule.get("rule_id", "")
        hint = rule.get("hint", "")
        kind = rule.get("kind")
        patterns = rule.get("patterns") or []
        compiled = [re.compile(pattern) for pattern in patterns]
        for file_path, line_no, content in added_lines:
            matched = False
            if kind == "subprocess_package_manager":
                matched = _subprocess_package_manager_line(content)
            else:
                for pattern in compiled:
                    if pattern.search(content):
                        matched = True
                        break
            if matched:
                violations.append(
                    domain_models.Violation(
                        rule_id=rule_id,
                        file=file_path,
                        line=line_no,
                        hint=hint,
                        detail=content.strip()[:200],
                    )
                )
    return violations
