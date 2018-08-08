# -*- mode: python -*-

block_cipher = None

a = Analysis(['../../start.py'],
             pathex=['../../'],
             binaries=[],
             datas=[('../../interfaces', 'interfaces')],
             hiddenimports=["colorlog", "tulipy", "vaderSentiment", "vaderSentiment.vaderSentiment",
             "tools.decoding_encoding", "newspaper", "pytrends", "pytrends.exceptions", "pytrends.request",
             "evaluator.Dispatchers.reddit_dispatcher", "evaluator.Dispatchers.twitter_dispatcher"],
             excludes=["tentacles", "tests", "logs",
             "trading.exchanges.websockets_exchanges.implementations.binance_websocket"],
             hookspath=[],
             runtime_hooks=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='start',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True )
