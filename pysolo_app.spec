# -*- mode: python -*-

from PyInstaller.utils.hooks import collect_submodules


block_cipher = None

datas = []
hiddenimports = []
hookspath = [
    'C:\\ProgramData\\Miniconda3\\envs\\pysolo-tools\\Lib\\site-packages\\PyInstaller\\hooks'
]

a = Analysis(['pysolo_app.py'],
             pathex=[
                 'C:\\Users\\goinac\\Work\\pysolo\\pysolo-tools',
                 'C:\\ProgramData\\Miniconda3\\envs\\pysolo-tools\\Lib',
                 'C:\\ProgramData\\Miniconda3\\envs\\pysolo-tools\\Lib\\encodings'
             ],
             binaries=[
             ],
             datas=datas,
             hiddenimports=hiddenimports,
             hookspath=hookspath,
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
