# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / "gui.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "resource"), "resource"), (str(root / "pattern.json"), ".")],
    hiddenimports=["pynput.keyboard._win32", "pynput.mouse._win32"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CleanerKota",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
