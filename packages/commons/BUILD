python_requirements(name="reqs")
python_requirements(name="full_reqs", source="full_requirements.txt")

python_sources(name="octobot_commons", sources=["octobot_commons/**/*.py"])

files(
    name="test_data",
    sources=["tests/static/**/*"],
)

python_test_utils(
    name="test_profiles_utils",
    sources=["tests/profiles/__init__.py"],
)

python_tests(
    name="tests",
    sources=["tests/**/test_*.py", "tests/profiles/**", "!tests/profiles/__init__.py"],
    dependencies=[":octobot_commons", ":reqs", ":full_reqs", "//:dev_reqs", ":test_data", ":test_profiles_utils"],
)