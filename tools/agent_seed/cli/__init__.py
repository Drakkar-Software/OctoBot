#  Demo-only agent seed CLI entrypoints.

import argparse
import typing

import tools.agent_seed.cli.all as agent_seed_cli_all
import tools.agent_seed.cli.bootstrap as agent_seed_cli_bootstrap
import tools.agent_seed.cli.seed as agent_seed_cli_seed


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.agent_seed")
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed", help="Write sync fixtures and demo wallet")
    seed_parser.add_argument("--user-folder", default=None)
    seed_parser.add_argument("--clear", action="store_true")
    seed_parser.add_argument("--repo-root", default=None)
    seed_parser.set_defaults(handler=agent_seed_cli_seed.run_from_namespace)

    bootstrap_parser = subparsers.add_parser(
        "bootstrap",
        help="POST automation_create and wait for RUNNING grid automation",
    )
    bootstrap_parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    bootstrap_parser.add_argument("--poll-interval", type=float, default=None)
    bootstrap_parser.add_argument("--timeout", type=float, default=None)
    bootstrap_parser.set_defaults(handler=agent_seed_cli_bootstrap.run_from_namespace)

    all_parser = subparsers.add_parser("all", help="Run seed then bootstrap")
    all_parser.add_argument("--user-folder", default=None)
    all_parser.add_argument("--clear", action="store_true")
    all_parser.add_argument("--repo-root", default=None)
    all_parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    all_parser.add_argument("--poll-interval", type=float, default=None)
    all_parser.add_argument("--timeout", type=float, default=None)
    all_parser.set_defaults(handler=agent_seed_cli_all.run_from_namespace)
    return parser


def main(argv: typing.Optional[list[str]] = None) -> int:
    arguments = build_arg_parser().parse_args(argv)
    return arguments.handler(arguments)
