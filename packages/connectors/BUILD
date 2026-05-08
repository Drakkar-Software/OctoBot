python_sources(name="octobot_connectors", sources=["octobot_connectors/**/*.py"])

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[":octobot_connectors", "//:dev_reqs"],
)
