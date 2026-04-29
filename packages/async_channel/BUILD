python_sources(name="async_channel", sources=["async_channel/**/*.py"])

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[":async_channel", "//:dev_reqs"],
)