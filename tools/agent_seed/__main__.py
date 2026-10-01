#  Demo-only agent seed CLI entrypoint.

import sys

import tools.agent_seed.cli as agent_seed_cli


if __name__ == "__main__":
    sys.exit(agent_seed_cli.main())
