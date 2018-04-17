# -*- mode: python -*-

block_cipher = None


a = Analysis(['pysolo_app.py'],
             pathex=[
                 'C:\\Users\\goinac\\Work\\pysolo\\pysolo-tools',
                 'C:\\ProgramData\\Miniconda3\\envs\\pysolo-tools\\Lib\\encodings'],
             binaries=[
                 ('C:\\ProgramData\\Miniconda3\\envs\\pysolo-tools\\Library\\plugins\\platforms\\qwindows.dll', 'qwindows.dll'),
                 ('C:\\ProgramData\\Miniconda3\\envs\\pysolo-tools\\Library\\lib\\opencv_core331.lib', 'opencv_core331.lib'),
                 ('C:\\ProgramData\\Miniconda3\\envs\\pysolo-tools\\Library\\bin\\opencv_ffmpeg331_64.dll', 'opencv_ffmpeg331_64.dll')
             ],
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
          a.binaries,
          name='pysolo_app',
          debug=False,
          strip=False,
          upx=False,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='pysolo_app')
