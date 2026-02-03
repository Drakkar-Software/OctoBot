python_requirements(name="full_reqs", source="full_requirements.txt")

python_sources(name="octobot_services", sources=["octobot_services/**/*.py"])

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[
        ":octobot_services",
        ":full_reqs",
        "//:dev_reqs",
        "packages/commons:octobot_commons",
        "packages/commons:reqs",
        "packages/commons:full_reqs",
        "packages/trading:octobot_trading",
        "packages/trading:reqs",
        "packages/trading:full_reqs",
    ],
)