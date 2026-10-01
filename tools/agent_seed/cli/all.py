#  Run seed then bootstrap.

import argparse

import tools.agent_seed.cli.bootstrap as agent_seed_cli_bootstrap
import tools.agent_seed.cli.seed as agent_seed_cli_seed


def run_from_namespace(arguments: argparse.Namespace) -> int:
    seed_exit = agent_seed_cli_seed.run_from_namespace(arguments)
    if seed_exit != 0:
        return seed_exit
    return agent_seed_cli_bootstrap.run_from_namespace(arguments)
