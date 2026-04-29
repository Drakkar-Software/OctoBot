python_requirements(name="reqs")

python_sources(name="octobot_node", sources=["octobot_node/**/*.py"])

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
        ":test_csv",
    ],
)