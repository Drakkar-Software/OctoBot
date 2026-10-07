#  Demo-only agent seed CLI entrypoints.

import argparse
import typing

import tools.agent_seed.cli.all as agent_seed_cli_all
import tools.agent_seed.cli.bootstrap as agent_seed_cli_bootstrap
import tools.agent_seed.cli.seed as agent_seed_cli_seed
import tools.agent_seed.cli.wait_for_base_url as agent_seed_cli_wait_for_base_url
import tools.agent_seed.enums as agent_seed_enums

_SCENARIO_CHOICES = [scenario.value for scenario in agent_seed_enums.BootstrapScenario]
_SCENARIO_HELP = "Bootstrap scenario, repeatable (default: grid). all = grid, index, completed, lifecycle"


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
        help="Start the seeded automations (grid by default) through the debug API",
    )
    bootstrap_parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    bootstrap_parser.add_argument("--poll-interval", type=float, default=None)
    bootstrap_parser.add_argument("--timeout", type=float, default=None)
    bootstrap_parser.add_argument(
        "--scenario", action="append", choices=_SCENARIO_CHOICES, default=None, help=_SCENARIO_HELP,
    )
    bootstrap_parser.set_defaults(handler=agent_seed_cli_bootstrap.run_from_namespace)

    all_parser = subparsers.add_parser("all", help="Run seed then bootstrap")
    all_parser.add_argument("--user-folder", default=None)
    all_parser.add_argument("--clear", action="store_true")
    all_parser.add_argument("--repo-root", default=None)
    all_parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    all_parser.add_argument("--poll-interval", type=float, default=None)
    all_parser.add_argument("--timeout", type=float, default=None)
    all_parser.add_argument(
        "--scenario", action="append", choices=_SCENARIO_CHOICES, default=None, help=_SCENARIO_HELP,
    )
    all_parser.set_defaults(handler=agent_seed_cli_all.run_from_namespace)

    wait_parser = subparsers.add_parser(
        "wait-for-base-url",
        help="Wait until the node accepts TCP connections on its base URL",
    )
    wait_parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    wait_parser.add_argument("--timeout", type=float, default=None)
    wait_parser.add_argument("--poll-interval", type=float, default=None)
    wait_parser.set_defaults(handler=agent_seed_cli_wait_for_base_url.run_from_namespace)
    return parser


def main(argv: typing.Optional[list[str]] = None) -> int:
    arguments = build_arg_parser().parse_args(argv)
    return arguments.handler(arguments)
