from setuptools import setup

from config.cst import VERSION

DESCRIPTION = open('README.md').read() + '\n\n' + open('docs/CHANGELOG.md').read()

REQUIRED = open('requirements.txt').read()

setup(
    name='OctoBot',
    version=VERSION,
    packages=['backtesting', 'config', 'docs', 'evaluator', 'interfaces', 'services', 'tests', 'tools', 'trading'],
    url='https://github.com/Drakkar-Software/OctoBot',
    license='MIT',
    author='Trading-Bot team',
    description='Cryptocurrencies alert / trading bot',
    long_description=DESCRIPTION,
    entry_points={
        'console_scripts': [
            'start = start:main',
        ],
    },
    zip_safe=False,
    install_requires=REQUIRED,
    setup_requires=['numpy', 'Cython', 'pytest-runner'],
    dependency_links=[
        'https://github.com/ccxt/ccxt.git'
    ],
    tests_require=[
        'pytest',
        'pytest-pep8',
        'pytest-cov',
        'coverage',
        'coveralls',
        'tox',
        'tox-travis'
    ],
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
)
