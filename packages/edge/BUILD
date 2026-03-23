python_requirements(name="reqs")
python_requirements(name="full_reqs", source="full_requirements.txt")

python_sources(name="octobot_edge", sources=["octobot_edge/**/*.py", "octobot_edge/**/*.pyi"])

files(
    name="test_data",
    sources=["tests/static/**/*"],
)

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[
        ":octobot_edge",
        ":reqs",
        ":full_reqs",
        "//:dev_reqs",
        ":test_data",
    ],
)

files(
    name="native_extension",
    sources=["octobot_edge/_native*.so", "octobot_edge/_native*.pyd", "octobot_edge/_native*.dylib"],
)

python_distribution(
    name="OctoBot-Edge",
    dependencies=[":octobot_edge", ":reqs", ":native_extension"],
    provides=python_artifact(
        name="octobot-edge",
        version="0.1.0",
        url="https://github.com/Drakkar-Software/OctoBot",
        license="GPL-3.0",
        author="Drakkar-Software",
        author_email="contact@drakkar.software",
        description="Universal CCXT wrapper for OctoBot — Python + JS, Rust-accelerated",
        long_description_file="ARCHITECTURE.md",
        long_description_content_type="text/markdown",
    ),
    generate_setup=True,
    sdist=True,
    wheel=True,
)
