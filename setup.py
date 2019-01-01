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

from setuptools import setup

from config import VERSION, PROJECT_LAUNCHER

DESCRIPTION = open('README.md').read() + '\n\n' + open('docs/CHANGELOG.md').read()

REQUIRED = open('pre_requirements.txt').read() + open('requirements.txt').read()
REQUIRED_DEV = open('dev_requirements.txt').read()

setup(
    name=PROJECT_LAUNCHER,
    version=VERSION,
    url='https://github.com/Drakkar-Software/OctoBot',
    license='LGPL-3.0',
    author='Drakkar-Software',
    author_email='drakkar.software@protonmail.com',
    description='Cryptocurrencies alert / trading bot',
    py_modules=['launcher'],
    packages=['interfaces.gui.launcher', 'interfaces.gui.util', 'config'],
    long_description=DESCRIPTION,
    install_requires=REQUIRED,
    tests_require=REQUIRED_DEV,
    test_suite="tests",
    zip_safe=False,
    python_requires='>=3.7',
    entry_points={
        'console_scripts': [
            PROJECT_LAUNCHER + ' = launcher:main'
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
    ],
)
