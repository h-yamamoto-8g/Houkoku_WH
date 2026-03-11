# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for 水質報告ツール (Houkoku)

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("resources/assets/splash.png", "resources/assets")],
    hiddenimports=[
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "matplotlib.backends.backend_tk",
        "matplotlib.backends.backend_tkagg",
        "PyQt5",
        "PyQt6",
        "tkinter",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

splash = Splash(
    "resources/assets/splash.png",
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
)

exe = EXE(
    pyz,
    splash,
    splash.binaries,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Houkoku",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="resources/assets/app-logo.ico",
)
