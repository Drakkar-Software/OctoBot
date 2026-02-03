python_requirements(name="reqs")
python_requirements(name="full_reqs", source="full_requirements.txt")
python_requirements(name="dev_reqs", source="dev_requirements.txt")

python_sources(name="octobot", sources=["octobot/**/*.py"])

files(
    name="octobot_config",
    sources=["octobot/config/**/*"],
)

files(
    name="octobot_strategy_optimizer_data",
    sources=["octobot/strategy_optimizer/optimizer_data_files/**/*"],
)

# For development purposes only
python_sources(name="tentacles", sources=["tentacles/**/*.py"])

resources(
    name="web_interface_resources",
    sources=[
        "tentacles/Services/Interfaces/web_interface/templates/**/*",
        "tentacles/Services/Interfaces/web_interface/static/**/*",
        "tentacles/Services/Interfaces/web_interface/advanced_templates/**/*"
    ]
)

PACKAGE_SOURCES = [
    "packages/async_channel:async_channel",
    "packages/backtesting:octobot_backtesting",
    "packages/commons:octobot_commons",
    "packages/evaluators:octobot_evaluators",
    "packages/node:octobot_node",
    "packages/services:octobot_services",
    "packages/tentacles_manager:octobot_tentacles_manager",
    "packages/trading:octobot_trading",
    "packages/trading_backend:trading_backend",
]

PACKAGE_REQS = [
    "packages/backtesting:reqs",
    "packages/commons:reqs",
    "packages/evaluators:reqs",
    "packages/node:reqs",
    "packages/tentacles_manager:reqs",
    "packages/trading:reqs",
    "packages/trading_backend:reqs",
]

PACKAGE_FULL_REQS = [
    "packages/commons:full_reqs",
    "packages/services:full_reqs",
    "packages/tentacles_manager:full_reqs",
    "packages/trading:full_reqs",
]

# Tests
files(
    name="test_data",
    sources=["tests/static/**/*"],
)

files(
    name="tentacles_test_data",
    sources=["tentacles/**/tests/static/**/*"],
)

# Test utilities (not actual tests, used by tests)
# Include all tests/ package files that are used by tentacles tests
python_sources(
    name="test_utils",
    sources=[
        "tests/**/*.py",
        "!tests/**/test_*.py",  # Exclude actual test files
    ],
)

# test_exchanges.py is a utility file (not a test) despite its name
# It must be a separate target to avoid glob ordering issues
python_source(
    name="test_exchanges_util",
    source="tests/test_utils/test_exchanges.py",
)

python_tests(
    name="tests",
    sources=[
        "tests/**/test_*.py",
        "tentacles/**/test_*.py",
        "!tests/test_utils/test_exchanges.py",
        "!tentacles/Trading/Exchange/**",
    ],
    dependencies=[
        ":reqs",
        ":full_reqs",
        ":dev_reqs",
        ":test_data",
        ":tentacles_test_data",
        ":test_utils",
        ":test_exchanges_util",
        ":web_interface_resources",
        ":octobot_config",
        ":octobot_strategy_optimizer_data",
        "//:tentacles",
        "packages/tentacles:tentacles_metadata",
        "packages/tentacles:tentacles_test_utils",
        "packages/tentacles:tentacles_test_data",
        ":octobot",
    ] + PACKAGE_SOURCES + PACKAGE_REQS + PACKAGE_FULL_REQS,
)

# Entrypoint
pex_binary(
    name="start",
    entry_point="octobot.cli:main",
    dependencies=[
        ":octobot",
        ":octobot_config",
        ":octobot_strategy_optimizer_data",
        ":reqs",
        ":full_reqs",
    ] + PACKAGE_SOURCES + PACKAGE_REQS + PACKAGE_FULL_REQS,
)

# Distributions
# Lite distribution - pants package :OctoBot-Lite
# python_distribution(
#     name="OctoBot-Lite",
#     dependencies=[
#         ":octobot",
#         ":reqs",
#     ] + PACKAGE_SOURCES + PACKAGE_REQS + PACKAGE_FULL_REQS,
#     provides=python_artifact(
#         name="octobot-lite",
#         version="2.0.16",
#     ),
#     sdist=True,
#     wheel=True,
# )

# Full distribution - pants package :OctoBot  
python_distribution(
    name="OctoBot",
    dependencies=[
        ":octobot",
        ":octobot_config",
        ":octobot_strategy_optimizer_data",
        ":reqs",
        ":full_reqs",
    ] + PACKAGE_SOURCES + PACKAGE_REQS + PACKAGE_FULL_REQS,
    provides=python_artifact(
        name="octobot",
        version="2.0.16",
    ),
    entry_points={
        'console_scripts': {
            'OctoBot': 'octobot.cli:main'
        }
    },
    sdist=True,
    wheel=True,
)

files(
    name="docker_files",
    sources=["docker/**/*"],
)

files(
    name="wheel_files",
    sources=["dist/"],
    dependencies=[":OctoBot"],
)

docker_image(
    name="docker",
    source="Dockerfile",
    dependencies=[
        ":OctoBot",
        ":wheel_files",
        ":octobot_config",
        ":octobot_strategy_optimizer_data",
        ":docker_files",
    ],
    repository="drakkarsoftware/octobot",
    image_tags=["local"],
    extra_build_args={
        "VERSION": "local",
        "TENTACLES_URL_TAG": "dev",
    },
    skip_push = True,
)
