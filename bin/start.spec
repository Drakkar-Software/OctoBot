# -*- mode: python -*-

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

block_cipher = None

# eth_account.hdaccount reads BIP39 wordlists from disk (hdaccount/wordlist/*.txt).
# hiddenimports only bundles Python modules; collect_data_files includes those data files.
eth_account_datas = collect_data_files("eth_account")

# importlib.metadata.version() at import time; PyInstaller does not bundle .dist-info by default.
_eth_web3_dist_names = (
   "py-ecc",
   "eth-account",
   "eth-keyfile",
   "eth-utils",
   "eth-typing",
   "eth-keys",
   "hexbytes",
   "web3",
)
eth_web3_metadata = []
for _dist_name in _eth_web3_dist_names:
   eth_web3_metadata += copy_metadata(_dist_name)

OCTOBOT_PACKAGES_FILES = REQUIRED = [s.strip() for s in open('bin/octobot_packages_files.txt').readlines()]
# hiddenimports=['numpy.core._dtype_ctypes'] from https://github.com/pyinstaller/pyinstaller/issues/3982
a = Analysis(
   ['../start.py'],
   pathex=['../'],
   datas=[
      ('../octobot/config', 'octobot/config'),
      ('../octobot/strategy_optimizer/optimizer_data_files', 'octobot/strategy_optimizer/optimizer_data_files'),
   ] + eth_account_datas + eth_web3_metadata,  # required for node wallet mnemonic generation (web3.Account.create_with_mnemonic)
   hiddenimports=[
      "colorlog", "numpy.core._dtype_ctypes", "dotenv",
      "pgpy", "imghdr",
      "web3", "eth_account",
      "aiosqlite", "aiohttp",
      "psutil",
      "telegram", "telegram.ext", "jsonschema",
      "tulipy",
      "asyncpraw", "simplifiedpytrends", "simplifiedpytrends.exceptions", "simplifiedpytrends.request",
      "pyngrok", "pyngrok.ngrok", "openai",
      "flask", "flask_login", "flask_wtf", "flask_socketio", "flask_cors",
      # Tentacles (excluded from Analysis) — ASGI stack per packages/services/full_requirements.txt
      "asgiref.sync", "asgiref.wsgi",
      "uvicorn", "uvicorn.config", "uvicorn.server",
      "starlette", "starlette.applications", "starlette.routing", "starlette.websockets",
      "werkzeug.middleware", "werkzeug.middleware.proxy_fix",
      "wtforms", "wtforms.fields",
      "vaderSentiment", "vaderSentiment.vaderSentiment",
      "coingecko_openapi_client",
      "certifi",
      "aiofiles",
      "pydantic", "mcp",
      "dbos", "fastapi", "passlib", "fastapi.staticfiles",
      "web3",
      "ccxt", "ccxt.async_support", "ccxt.pro", "order_book", "cmath", "cryptography", "websockets", "yarl", "idna", "sortedcontainers",
      "websockets.legacy", "websockets.legacy.auth", "websockets.legacy.client", "websockets.legacy.compatibility",
      "websockets.legacy.framing", "websockets.legacy.handshake", "websockets.legacy.http", "websockets.legacy.protocol",
      "websockets.legacy.server"
   ] + OCTOBOT_PACKAGES_FILES,
   excludes=["tentacles", "logs", "user"],
   hookspath=[],
   runtime_hooks=[],
   win_no_prefer_redirects=False,
   win_private_assemblies=False,
   cipher=block_cipher
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='OctoBot',
          debug=False,
          strip=False,
          icon="favicon.ico",
          upx=True,
          runtime_tmpdir=None,
          console=True )
