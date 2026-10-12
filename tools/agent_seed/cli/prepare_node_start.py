#  prepare-node-start subcommand CLI (port / pidfile checks before background start).

import argparse
import os
import sys
import typing

import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.operations.node_lifecycle as agent_seed_node_lifecycle
import tools.agent_seed.paths as agent_seed_paths


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail fast if the agent-seed node port is busy or a recorded node is still running",
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
    return parser


def _resolve_user_folder(user_folder: typing.Optional[str]) -> typing.Optional[str]:
    if user_folder is not None:
        return user_folder
    return os.environ.get("OCTOBOT_AGENT_SEED_USER_FOLDER")


def main(argv: typing.Optional[list[str]] = None) -> int:
    arguments = build_arg_parser().parse_args(argv)
    user_folder_value = _resolve_user_folder(arguments.user_folder)
    if not user_folder_value:
        print(
            "prepare-node-start requires --user-folder or OCTOBOT_AGENT_SEED_USER_FOLDER",
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
        agent_seed_node_lifecycle.prepare_node_start(
            user_folder=user_folder,
            base_url=arguments.base_url,
        )
    except agent_seed_errors.AgentSeedPortInUseError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


def run_from_namespace(arguments: argparse.Namespace) -> int:
    prepare_argv: list[str] = ["--base-url", arguments.base_url]
    if arguments.user_folder is not None:
        prepare_argv.extend(["--user-folder", arguments.user_folder])
    return main(prepare_argv)
