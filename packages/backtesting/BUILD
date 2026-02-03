python_requirements(name="reqs")

python_sources(name="octobot_backtesting", sources=["octobot_backtesting/**/*.py"])

files(
    name="test_data",
    sources=["tests/static/**/*"],
)

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[
        ":octobot_backtesting",
        ":reqs",
        "//:dev_reqs",
        ":test_data",
        "packages/commons:octobot_commons",
        "packages/commons:reqs",
        "packages/commons:full_reqs",
    ],
)