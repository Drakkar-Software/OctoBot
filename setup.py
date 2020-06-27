#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import os
from setuptools import dist

dist.Distribution().fetch_build_eggs(['Cython>=0.29.20'])

try:
    from Cython.Distutils import build_ext
    from Cython.Build import cythonize
except ImportError:
    # create closure for deferred import
    def cythonize(*args, **kwargs):
        from Cython.Build import cythonize
        return cythonize(*args, **kwargs)

    def build_ext(*args, **kwargs):
        from Cython.Distutils import build_ext
        return build_ext(*args, **kwargs)

from setuptools import find_packages
from setuptools import setup, Extension
from octobot.constants import PROJECT_NAME, VERSION

PACKAGES = find_packages(exclude=["tentacles*"])

packages_list = ["octobot.initializer",
                 "octobot.configuration_manager",
                 "octobot.task_manager",
                 "octobot.api.octobot_api",
                 "octobot.octobot",
                 "octobot.channels.octobot_channel",
                 "octobot.consumers.octobot_channel_consumer",
                 "octobot.producers.evaluator_producer",
                 "octobot.producers.exchange_producer",
                 "octobot.producers.interface_producer",
                 "octobot.producers.service_feed_producer",
                 "octobot.backtesting.octobot_backtesting",
                 "octobot.backtesting.octobot_backtesting_factory",
                 "octobot.backtesting.independent_backtesting",
                 "octobot.backtesting.abstract_backtesting_test",
                 "octobot.strategy_optimizer.strategy_test_suite",
                 "octobot.strategy_optimizer.test_suite_result",
                 "octobot.strategy_optimizer.strategy_optimizer"]

ext_modules = [
    Extension(package, [f"{package.replace('.', '/')}.py"])
    for package in packages_list]

# long description from README file
with open('README.md', encoding='utf-8') as f:
    DESCRIPTION = f.read()

REQUIRED = open('requirements.txt').readlines()
REQUIRES_PYTHON = '>=3.7'
CYTHON_DEBUG = False if not os.getenv('CYTHON_DEBUG') else os.getenv('CYTHON_DEBUG')

setup(
    name=PROJECT_NAME,
    version=VERSION,
    url='https://github.com/Drakkar-Software/OctoBot',
    license='LGPL-3.0',
    author='Drakkar-Software',
    author_email='drakkar-software@protonmail.com',
    description='Cryptocurrencies alert / trading bot',
    py_modules=['start'],
    packages=PACKAGES,
    package_data={
        "": ["config/*", "strategy_optimizer/optimizer_data_files/*"],
    },
    long_description=DESCRIPTION,
    long_description_content_type='text/markdown',
    cmdclass={'build_ext': build_ext},
    tests_require=["pytest"],
    test_suite="tests",
    zip_safe=False,
    setup_requires=REQUIRED if not CYTHON_DEBUG else [],
    install_requires=REQUIRED,
    ext_modules=cythonize(ext_modules, gdb_debug=CYTHON_DEBUG),
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
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Cython'
    ],
)
