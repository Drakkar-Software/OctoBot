python_requirements(name="reqs")

python_sources(name="octobot_node", sources=["octobot_node/**/*.py"])

python_source(
    name="test_conftest",
    source="tests/conftest.py",
)

files(
    name="test_csv",
    sources=["tests/**/*.csv"],
)

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[
        ":octobot_node",
        ":reqs",
        "//:dev_reqs",
        ":test_conftest",
        ":test_csv",
    ],
)