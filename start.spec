# -*- mode: python -*-

block_cipher = None


a = Analysis(['start.py'],
             pathex=['/home/herklos/dev/drakkars/OctoBot'],
             binaries=[],
             datas=[],
             hiddenimports=["colorlog"],
             excludes=["tentacles", "tests", "docs"],
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
