#  Demo-only agent seed CLI entrypoints.

import argparse
import os
import pathlib
import sys
import typing

import tools.agent_seed.cli.all as agent_seed_cli_all
import tools.agent_seed.cli.bootstrap as agent_seed_cli_bootstrap
import tools.agent_seed.cli.seed as agent_seed_cli_seed
import tools.agent_seed.cli.wait_for_base_url as agent_seed_cli_wait_for_base_url
import tools.agent_seed.enums as agent_seed_enums
import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.operations.node_lifecycle as agent_seed_node_lifecycle
import tools.agent_seed.paths as agent_seed_paths

_SCENARIO_CHOICES = [scenario.value for scenario in agent_seed_enums.BootstrapScenario]
_SCENARIO_HELP = "Bootstrap scenario, repeatable (default: grid). all = grid, index, completed, lifecycle"

_DEFAULT_BASE_URL = os.environ.get("AGENT_SEED_BASE_URL", "http://127.0.0.1:8000")


def _run_stop_node(arguments: argparse.Namespace) -> int:
    user_folder = agent_seed_paths.resolve_agent_seed_user_folder(arguments.user_folder)
    if user_folder is None:
        print(
            "stop-node requires --user-folder or OCTOBOT_AGENT_SEED_USER_FOLDER",
            file=sys.stderr,
        )
        return 1
    try:
        message = agent_seed_node_lifecycle.stop_recorded_node(
            user_folder=user_folder,
            base_url=arguments.base_url,
            stop_timeout_seconds=agent_seed_node_lifecycle.resolve_stop_timeout_seconds(
                arguments.stop_timeout,
            ),
        )
    except agent_seed_errors.AgentSeedNodeStopError as error:
        print(error, file=sys.stderr)
        return 1
    print(message)
    return 0


def _run_start_background(arguments: argparse.Namespace) -> int:
    repo_root = pathlib.Path(arguments.repo_root).resolve()
    user_folder = agent_seed_paths.resolve_agent_seed_user_folder(
        arguments.user_folder,
        repo_root=repo_root,
    )
    if user_folder is None:
        print(
            "start-background requires --user-folder or OCTOBOT_AGENT_SEED_USER_FOLDER",
            file=sys.stderr,
        )
        return 1
    try:
        message = agent_seed_node_lifecycle.start_node_background(
            user_folder=user_folder,
            base_url=arguments.base_url,
            repo_root=repo_root,
        )
    except agent_seed_errors.AgentSeedPortInUseError as error:
        print(error, file=sys.stderr)
        return 1
    print(message)
    return 0


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
    bootstrap_parser.add_argument("--base-url", default=_DEFAULT_BASE_URL)
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
    all_parser.add_argument("--base-url", default=_DEFAULT_BASE_URL)
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
    wait_parser.add_argument("--base-url", default=_DEFAULT_BASE_URL)
    wait_parser.add_argument("--timeout", type=float, default=None)
    wait_parser.add_argument("--poll-interval", type=float, default=None)
    wait_parser.set_defaults(handler=agent_seed_cli_wait_for_base_url.run_from_namespace)

    stop_parser = subparsers.add_parser(
        "stop-node",
        help="Stop the background agent-seed OctoBot node and verify its port is free",
    )
    stop_parser.add_argument("--user-folder", default=None)
    stop_parser.add_argument("--base-url", default=_DEFAULT_BASE_URL)
    stop_parser.add_argument("--stop-timeout", type=float, default=None)
    stop_parser.set_defaults(handler=_run_stop_node)

    start_background_parser = subparsers.add_parser(
        "start-background",
        help="Prepare port/pidfile and start OctoBot detached for agent-seed demo",
    )
    start_background_parser.add_argument("--user-folder", default=None)
    start_background_parser.add_argument("--base-url", default=_DEFAULT_BASE_URL)
    start_background_parser.add_argument(
        "--repo-root",
        default=str(agent_seed_paths.default_octobot_repo_root()),
        help="OctoBot repo root (start.py cwd)",
    )
    start_background_parser.set_defaults(handler=_run_start_background)
    return parser


def main(argv: typing.Optional[list[str]] = None) -> int:
    arguments = build_arg_parser().parse_args(argv)
    return arguments.handler(arguments)
