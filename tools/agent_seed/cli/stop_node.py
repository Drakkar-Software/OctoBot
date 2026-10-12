#  stop-node subcommand CLI.

import argparse
import os
import sys
import typing

import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.operations.node_lifecycle as agent_seed_node_lifecycle
import tools.agent_seed.paths as agent_seed_paths


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stop the agent-seed background OctoBot node recorded in the user-folder pidfile",
    )
    parser.add_argument(
        "--user-folder",
        default=None,
        help="Demo user folder (default: OCTOBOT_AGENT_SEED_USER_FOLDER)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("AGENT_SEED_BASE_URL", "http://127.0.0.1:8000"),
        help="Node API base URL (default: AGENT_SEED_BASE_URL or http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--stop-timeout",
        type=float,
        default=None,
        help=(
            "Seconds to wait for graceful shutdown "
            f"(default: AGENT_SEED_STOP_WAIT_SEC or "
            f"{agent_seed_node_lifecycle.DEFAULT_STOP_TIMEOUT_SECONDS:g})"
        ),
    )
    return parser


def _resolve_user_folder(user_folder: typing.Optional[str]) -> typing.Optional[str]:
    if user_folder is not None:
        return user_folder
    return os.environ.get("OCTOBOT_AGENT_SEED_USER_FOLDER")


def _resolve_stop_timeout_seconds(stop_timeout: typing.Optional[float]) -> float:
    if stop_timeout is not None:
        return stop_timeout
    env_value = os.environ.get("AGENT_SEED_STOP_WAIT_SEC")
    if env_value is not None:
        return float(env_value)
    return agent_seed_node_lifecycle.DEFAULT_STOP_TIMEOUT_SECONDS


def main(argv: typing.Optional[list[str]] = None) -> int:
    arguments = build_arg_parser().parse_args(argv)
    user_folder_value = _resolve_user_folder(arguments.user_folder)
    if not user_folder_value:
        print(
            "stop-node requires --user-folder or OCTOBOT_AGENT_SEED_USER_FOLDER",
            file=sys.stderr,
        )
        return 1
    user_folder = agent_seed_paths.resolve_path_from_env(
        user_folder_value,
        agent_seed_paths.default_octobot_repo_root(),
    )
    if user_folder is None:
        print("Could not resolve agent-seed user folder path", file=sys.stderr)
        return 1
    try:
        message = agent_seed_node_lifecycle.stop_recorded_node(
            user_folder=user_folder,
            base_url=arguments.base_url,
            stop_timeout_seconds=_resolve_stop_timeout_seconds(arguments.stop_timeout),
        )
    except agent_seed_errors.AgentSeedNodeStopError as error:
        print(error, file=sys.stderr)
        return 1
    print(message)
    return 0


def run_from_namespace(arguments: argparse.Namespace) -> int:
    stop_argv: list[str] = ["--base-url", arguments.base_url]
    if arguments.user_folder is not None:
        stop_argv.extend(["--user-folder", arguments.user_folder])
    if arguments.stop_timeout is not None:
        stop_argv.extend(["--stop-timeout", str(arguments.stop_timeout)])
    return main(stop_argv)
