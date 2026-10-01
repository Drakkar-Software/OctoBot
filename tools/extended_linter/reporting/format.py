import json
import typing

import tools.extended_linter.domain.models as domain_models


def format_text(violations: list[domain_models.Violation]) -> str:
    if not violations:
        return "extended_linter: OK (0 violations)"
    blocks: list[str] = []
    for violation in violations:
        location = violation.file or "(git)"
        if violation.line is not None:
            location = f"{location}:{violation.line}"
        block = (
            f"[{violation.rule_id}] {location}\n"
            f"  hint: {violation.hint}"
        )
        if violation.detail:
            block += f"\n  detail: {violation.detail}"
        blocks.append(block)
    header = f"extended_linter: FAIL ({len(violations)} violation(s))"
    return header + "\n\n" + "\n\n".join(blocks)


def format_json(violations: list[domain_models.Violation]) -> str:
    payload: dict[str, typing.Any] = {
        "ok": len(violations) == 0,
        "violation_count": len(violations),
        "violations": [violation.to_dict() for violation in violations],
    }
    return json.dumps(payload, indent=2)
