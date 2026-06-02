python_requirements(name="reqs")

python_sources(name="octobot_tunnel", sources=["octobot_tunnel/**/*.py"])

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[
        ":octobot_tunnel",
        ":reqs",
        "//:dev_reqs",
    ],
)
