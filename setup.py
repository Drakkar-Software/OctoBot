import os

from Cython.Build import cythonize
from setuptools import setup, Extension

from config.cst import VERSION

NAME = "OctoBot"
DESCRIPTION = open('README.md').read() + '\n\n' + open('docs/CHANGELOG.md').read()

REQUIRED = open('requirements.txt').read()
REQUIRED_DEV = open('dev_requirements.txt').read()

# building
excluded_files = ["setup.py", "__init__.py"]
excluded_folder = ["tentacles", "tests", "docs", "logs"]
source_files = [os.path.join(root, name)
                for root, dirs, files in os.walk(".")
                for name in files
                if name.endswith(".py") and name not in excluded_files and dirs not in excluded_folder]

extensions = [
    Extension(NAME, source_files),
]

setup(
    name=NAME,
    version=VERSION,
    url='https://github.com/Drakkar-Software/OctoBot',
    license='Apache-2.0',
    author='Trading-Bot team',
    description='Cryptocurrencies alert / trading bot',
    long_description=DESCRIPTION,
    install_requires=REQUIRED,
    tests_require=REQUIRED_DEV,
    test_suite="tests",
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    ext_modules=cythonize(extensions,
                          build_dir="build",
                          compiler_directives={"boundscheck": False,
                                               "language_level": 3}),
)
