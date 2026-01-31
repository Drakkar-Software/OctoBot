python_sources(name="octobot_tentacles", sources=["**/*.py", "!**/tests/**/*.py", "!conftest.py"])

# Tentacles test utilities (non-test files within tests directories that are imported by other tests)
python_sources(
    name="tentacles_test_utils",
    sources=[
        "**/tests/**/*.py",
        "!**/tests/**/test_*.py",  # Exclude actual test files
    ],
)

files(
    name="tentacles_metadata",
    sources=["**/metadata.json", "**/config/**/*", "metadata.yaml", "octobot_config.json"],
)

# Static test files (JSON configs, data files, etc.) used by tentacles tests
files(
    name="tentacles_test_data",
    sources=["**/tests/static/**/*"],
)
