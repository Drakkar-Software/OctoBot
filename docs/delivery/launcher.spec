# -*- mode: python -*-

block_cipher = None


a = Analysis(['../../launcher.py'],
             pathex=['../../'],
             binaries=[],
             datas=[('../../interfaces/web', 'interfaces/web')],
             hiddenimports=["glob", "subprocess", "json", "requests", "os", "logging",
             "tkinter", "tkinter.ttk", "tkinter.dialog", "tkinter.dialog", "tkinter.messagebox",
             "distutils", "distutils.version", "config", "logging"],
             hookspath=[],
             runtime_hooks=[],
             excludes=["interfaces.gui.launcher"],
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
          icon="../../interfaces/web/static/favicon.ico",
          upx=True,
          runtime_tmpdir=None,
          console=True )
