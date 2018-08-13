# -*- mode: python -*-

block_cipher = None


a = Analysis(['../../launcher.py'],
             pathex=['/home/herklos/dev/drakkars/OctoBot'],
             binaries=[],
             datas=[('../../interfaces', 'interfaces')],
             hiddenimports=["glob", "subprocess", "json"],
             hookspath=[],
             runtime_hooks=[],
             excludes=["interfaces.launcher"],
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
          name='launcher',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True )
