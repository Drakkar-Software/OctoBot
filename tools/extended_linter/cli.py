import argparse
import pathlib
import sys

import tools.extended_linter.config.loader as config_loader
import tools.extended_linter.engine.runner as engine_runner
import tools.extended_linter.reporting.format as reporting_format


def _find_repo_root() -> pathlib.Path:
    candidate = pathlib.Path.cwd().resolve()
    for path in [candidate, *candidate.parents]:
        if (path / ".git").is_dir():
            return path
    return candidate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="extended_linter",
        description="OctoBot PR policy linter (git scope, paths, diff content)",
    )
    parser.add_argument(
        "--base",
        default="origin/dev",
        help="Merge base git ref (default: origin/dev)",
    )
    parser.add_argument(
        "--repo-root",
        type=pathlib.Path,
        default=None,
        help="OctoBot repository root (default: nearest .git from cwd)",
    )
    parser.add_argument(
        "--policy",
        type=pathlib.Path,
        default=None,
        help="Path to policy.yaml (default: bundled policy)",
    )
    parser.add_argument(
        "--report",
        choices=("text", "json"),
        default="text",
        help="Report format (default: text)",
    )
    parser.add_argument(
        "--continue",
        dest="continue_on_violation",
        action="store_true",
        help="Always run all checks (default; same as omitting stop-on-first)",
    )
    parser.add_argument(
        "--skip-tentacles-reinstall",
        action="store_true",
        help="Do not run reinstall-tentacles.sh when tentacles sources change",
    )
    parser.add_argument(
        "--write-report",
        type=pathlib.Path,
        default=None,
        help="Write report file (format from --report)",
    )
    parser.add_argument(
        "--write-report-json",
        type=pathlib.Path,
        default=None,
        help="Also write JSON report to this path (single run, any --report stdout format)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = args.repo_root or _find_repo_root()
    try:
        config_loader.load_policy(args.policy)
    except config_loader.PolicyLoadError as error:
        print(f"extended_linter: policy error: {error}", file=sys.stderr)
        return 2
    config = engine_runner.RunnerConfig(
        repo_root=repo_root,
        base_ref=args.base,
        policy_path=args.policy,
        skip_tentacles_reinstall=args.skip_tentacles_reinstall,
    )
    violations = engine_runner.run(config)
    if args.report == "json":
        output = reporting_format.format_json(violations)
    else:
        output = reporting_format.format_text(violations)
    print(output)
    if args.write_report is not None:
        args.write_report.write_text(output, encoding="utf-8")
    if args.write_report_json is not None:
        args.write_report_json.write_text(
            reporting_format.format_json(violations),
            encoding="utf-8",
        )
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
