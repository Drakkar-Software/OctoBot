python_sources(name="octobot_poc", sources=["octobot_poc/**/*.py"])

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[":octobot_poc", "//:dev_reqs"],
)
