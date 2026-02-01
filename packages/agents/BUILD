python_sources(name="octobot_agents", sources=["octobot_agents/**/*.py"])

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[
        ":octobot_agents",
        ":reqs",
        ":full_reqs",
        "//:dev_reqs",
        "packages/commons:octobot_commons",
        "packages/commons:reqs",
        "packages/commons:full_reqs",
        "packages/services:octobot_services",
        "packages/services:reqs",
        "packages/services:full_reqs",
    ],
)