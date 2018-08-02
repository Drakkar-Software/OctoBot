import os

from Cython.Build import cythonize
from setuptools import setup, Extension, find_packages

from config.cst import VERSION

NAME = "OctoBot"
DESCRIPTION = open('README.md').read() + '\n\n' + open('docs/CHANGELOG.md').read()

REQUIRED = open('requirements.txt').read()
REQUIRED_DEV = open('dev_requirements.txt').read()

# building
packages = find_packages()
excluded_dirs = ["tentacles"]
extensions = [
    Extension(package, [os.path.join(root, name)
                        for root, dirs, files in os.walk(f"./{package.replace('.', os.path.sep)}")
                        for name in files
                        if name.endswith(".py")])
    for package in packages
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
