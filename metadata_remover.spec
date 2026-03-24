# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

textual_datas = collect_data_files("textual")

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=textual_datas,
    hiddenimports=[
        "textual.widgets",
        "textual.screen",
        "textual.containers",
        "textual._ansi_theme",
        "zlib",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="metadata-remover",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    target_arch=None,
)
