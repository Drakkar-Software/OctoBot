python_requirements(
    name="reqs",
    module_mapping={
        "OctoBot-Tulipy": ["tulipy"],
    },
)

python_sources(name="octobot_evaluators", sources=["octobot_evaluators/**/*.py"])

files(
    name="test_data",
    sources=["tests/static/**/*"],
)

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[
        ":octobot_evaluators",
        ":reqs",
        "//:dev_reqs",
        ":test_data",
        "packages/commons:octobot_commons",
        "packages/commons:reqs",
        "packages/commons:full_reqs",
        "packages/tentacles_manager:octobot_tentacles_manager",
        "packages/tentacles_manager:reqs",
        "packages/tentacles_manager:full_reqs"
    ],
)