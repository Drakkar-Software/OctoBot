python_requirements(name="reqs")

python_sources(name="trading_backend", sources=["trading_backend/**/*.py"])

python_sources(
    name="test_util",
    sources=["tests/**/*.py", "!tests/test_*.py", "!tests/conftest.py"],
)

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[
        ":trading_backend",
        ":reqs",
        "//:dev_reqs",
        ":test_util",
        "packages/commons:octobot_commons",
        "packages/commons:reqs",
        "packages/commons:full_reqs",
    ],
)