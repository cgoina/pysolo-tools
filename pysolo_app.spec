# -*- mode: python -*-

block_cipher = None


a = Analysis(['pysolo_app.py'],
             pathex=['C:\\Users\\goinac\\Work\\pysolo\\pysolo-tools'],
             binaries=[('C:\\ProgramData\\Miniconda3\\envs\\pysolo-tools\\Library\\plugins\\platforms\\qwindows.dll')],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=False,
          name='pysolo_app',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='pysolo_app')
