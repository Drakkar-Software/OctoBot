from setuptools import setup

from config.cst import VERSION

DESCRIPTION = open('README.md').read() + '\n\n' + open('docs/CHANGELOG.md').read()

setup(
    name='OctoBot',
    version=VERSION,
    # TODO packages=[''],
    url='https://github.com/Drakkar-Software/OctoBot',
    license='MIT',
    author='Trading-Bot team',
    description='Cryptocurrencies alert / trading bot',
    long_description=DESCRIPTION,
    entry_points={
        'console_scripts': [
            'coveralls = coveralls.cli:main',
        ],
    },
    # TODO install_requires=[],
    setup_requires=['pytest-runner'],
    # TODO  tests_require=[],
    # TODO  extras_require={},
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
)
