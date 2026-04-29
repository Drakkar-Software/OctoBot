python_requirements(name="reqs")
python_requirements(name="full_reqs", source="full_requirements.txt")

python_sources(name="octobot_trading", sources=["octobot_trading/**/*.py"])

files(
    name="test_data",
    sources=["tests/static/**/*"],
)

python_sources(
    name="test_support_files",
    sources=["tests/**/*.py", "!tests/**/test_*.py", "!tests/conftest.py"],
)

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[
        ":octobot_trading",
        ":reqs",
        ":full_reqs",
        "//:dev_reqs",
        ":test_data",
        ":test_support_files",
        "packages/commons:octobot_commons",
        "packages/commons:reqs",
        "packages/commons:full_reqs",
        "packages/tentacles_manager:octobot_tentacles_manager",
        "packages/tentacles_manager:reqs",
        "packages/tentacles_manager:full_reqs",
    ],
)