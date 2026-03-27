import sys
import os


def pytest_addoption(parser):
    parser.addoption(
        "--backend",
        default="python",
        choices=["python", "rust"],
        help="Which octobot_poc backend to test (python or rust)",
    )


def pytest_configure(config):
    backend = config.getoption("--backend", default="python")
    os.environ["OCTOBOT_POC_TEST_BACKEND"] = backend
    if backend != "rust":
        return

    import octobot_poc_rs  # pylint: disable=import-outside-toplevel,import-error

    submodules = {
        "octobot_poc": octobot_poc_rs,
        "octobot_poc.greeting": octobot_poc_rs,
    }
    sys.modules.update(submodules)
    octobot_poc_rs.greeting = octobot_poc_rs
