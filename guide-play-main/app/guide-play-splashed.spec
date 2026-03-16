# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['guiBeta.py'],
    pathex=[],
    binaries=[],
    datas=[('tesseract', 'tesseract/'), ('extraLibs', 'extraLibs/'),  ('ocr_wrapper', 'ocr_wrapper/'), ('server', 'server/'), ('models', 'models/'), ('UI', 'UI/'), ('assets', 'assets/'), ('AppComponents', 'AppComponents/')],
    hiddenimports=['webview', 'olefile'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hooks.py'],
    excludes=[],
    noarchive=True,
)
pyz = PYZ(a.pure)
splash = Splash(
    'UI/images/splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    [('v', None, 'OPTION')],
    exclude_binaries=True,
    name='guide-play',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon=['assets\\app-icon.ico'],
    hide_console='hide-early',
    manifest='manifest.xml',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    splash.binaries,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='guide-play',
)
