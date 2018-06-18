from setuptools import setup

from config.cst import VERSION

DESCRIPTION = open('README.md').read() + '\n\n' + open('docs/CHANGELOG.md').read()

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
    install_requires=['numpy',
                      'pandas',
                      'matplotlib==2.2.2',
                      'requests',
                      'vaderSentiment',
                      'pytrends',
                      'twisted==18.4.0',
                      'python-binance',
                      'colorlog',
                      'Python-Twitter',
                      'psutil',
                      'plotly',
                      'newspaper3k',
                      'praw',
                      'python-telegram-bot',
                      'dash',
                      'dash-table-experiments',
                      'flask',
                      'dash-renderer',
                      'dash-html-components',
                      'dash-core-components',
                      'cryptography >= 2.2.1',
                      'tulipy'],
    setup_requires=['numpy', 'Cython', 'pytest-runner'],
    dependency_links=[
        'https://github.com/ccxt/ccxt.git',
        'https://github.com/fxsjy/jieba.git'
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
