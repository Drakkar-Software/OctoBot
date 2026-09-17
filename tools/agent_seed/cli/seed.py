#  Seed subcommand CLI.

import argparse
import os
import pathlib
import typing

import tools.agent_seed.operations.seed_run as agent_seed_seed_run
import tools.agent_seed.paths as agent_seed_paths


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed demo agent-seed sync fixtures")
    parser.add_argument(
        "--user-folder",
        default=os.environ.get("OCTOBOT_AGENT_SEED_USER_FOLDER"),
        help="User data folder (default: OCTOBOT_AGENT_SEED_USER_FOLDER)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Wipe user folder and scheduler sqlite before seeding",
    )
    parser.add_argument(
        "--repo-root",
        default=str(agent_seed_paths.default_octobot_repo_root()),
        help="OctoBot repo root for relative env paths",
    )
    return parser


def main(argv: typing.Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    arguments = parser.parse_args(argv)
    if not arguments.user_folder:
        parser.error("user folder is required (set OCTOBOT_AGENT_SEED_USER_FOLDER or --user-folder)")
    repo_root = pathlib.Path(arguments.repo_root).resolve()
    user_folder = agent_seed_paths.resolve_path_from_env(arguments.user_folder, repo_root)
    if user_folder is None:
        parser.error("invalid user folder path")
    node_sqlite_file = agent_seed_paths.resolve_path_from_env(
        os.environ.get("NODE_SQLITE_FILE"),
        repo_root,
    )
    agent_seed_seed_run.run_seed(
        user_folder=user_folder,
        clear=arguments.clear,
        node_sqlite_file=node_sqlite_file,
        repo_root=repo_root,
    )
    return 0


def run_from_namespace(arguments: argparse.Namespace) -> int:
    seed_argv: list[str] = []
    if arguments.user_folder:
        seed_argv.extend(["--user-folder", arguments.user_folder])
    if arguments.clear:
        seed_argv.append("--clear")
    if arguments.repo_root:
        seed_argv.extend(["--repo-root", arguments.repo_root])
    return main(seed_argv)
