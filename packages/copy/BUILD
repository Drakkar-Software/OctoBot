python_sources(
    name="octobot_copy",
    sources=["octobot_copy/**/*.py"],
    dependencies=[
        "packages/commons:octobot_commons",
        "packages/trading:octobot_trading",
        "//:tentacles",
    ],
)

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[
        ":octobot_copy",
    ],
)