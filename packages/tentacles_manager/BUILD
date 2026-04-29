python_requirements(name="reqs")
python_requirements(name="full_reqs", source="full_requirements.txt")

python_sources(name="octobot_tentacles_manager", sources=["octobot_tentacles_manager/**/*.py"])

files(
    name="test_data",
    sources=["tests/static/**/*"],
)

python_sources(
    name="test_helpers",
    sources=["tests/__init__.py", "tests/api/__init__.py", "tests/exporters/__init__.py"],
)

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[
        ":octobot_tentacles_manager",
        ":reqs",
        ":full_reqs",
        "//:dev_reqs",
        ":test_data",
        ":test_helpers",
        "packages/commons:octobot_commons",
        "packages/commons:reqs",
        "packages/commons:full_reqs",
    ],
)