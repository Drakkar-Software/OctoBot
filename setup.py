#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import sys
import os
from setuptools import find_packages
from setuptools import setup
from octobot import PROJECT_NAME, AUTHOR, VERSION

is_building_wheel = "bdist_wheel" in sys.argv

EXCLUDED_PACKAGES = ["tentacles*", "tests"]
DATA_FILES = ["config/*", "strategy_optimizer/optimizer_data_files/*"]
if is_building_wheel and bool(os.getenv("USE_MINIMAL_LIBS", "false").lower() == "true"):
    # exclude data files when building a wheel with minimal libs
    DATA_FILES = []
PACKAGES = [
    pkg for pkg in find_packages(exclude=EXCLUDED_PACKAGES)
    if not any(
        # manually excluded packages as they can't be excluded from a wheel otherwise 
        # because those are valid python packages
        str(pkg).startswith(excluded_package)
        for excluded_package in EXCLUDED_PACKAGES
    )
]
# Include octobot_agents from packages/agents/octobot_agents
PACKAGES.extend(find_packages(where='packages/agents'))

# long description from README file
with open('README.md', encoding='utf-8') as f:
    DESCRIPTION = f.read()


def ignore_git_requirements(requirements):
    return [requirement for requirement in requirements if "git+" not in requirement]


REQUIRED = ignore_git_requirements(open('requirements.txt').readlines())
FULL_REQUIRED = ignore_git_requirements(open('full_requirements.txt').readlines())
REQUIRES_PYTHON = '>=3.13'

setup(
    name=PROJECT_NAME.lower().replace("-", "_"),
    version=VERSION,
    url='https://github.com/Drakkar-Software/OctoBot',
    license='GPL-3.0',
    author=AUTHOR,
    author_email='contact@drakkar.software',
    description='Cryptocurrencies alert / trading bot',
    py_modules=['start'],
    packages=PACKAGES,
    package_dir={'octobot_agents': 'packages/agents/octobot_agents'},
    package_data={
        "": DATA_FILES,
    },
    long_description=DESCRIPTION,
    long_description_content_type='text/markdown',
    tests_require=["pytest"],
    test_suite="tests",
    zip_safe=False,
    install_requires=REQUIRED,
    extras_require={
        'full': FULL_REQUIRED,
    },
    python_requires=REQUIRES_PYTHON,
    entry_points={
        'console_scripts': [
            PROJECT_NAME + ' = octobot.cli:main'
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.13',
    ],
)
