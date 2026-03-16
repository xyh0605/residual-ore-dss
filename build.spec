# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build spec - Residual Ore Recovery DSS
# Usage: pyinstaller --noconfirm build.spec

import sys
block_cipher = None

a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'streamlit',
        'streamlit.runtime',
        'streamlit.runtime.scriptrunner',
        'streamlit.web',
        'plotly',
        'plotly.express',
        'plotly.graph_objects',
        'plotly.subplots',
        'sklearn',
        'sklearn.neighbors',
        'sklearn.preprocessing',
        'pandas',
        'numpy',
        'openpyxl',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'PyQt5', 'PySide2'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ResidualOreDSS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ResidualOreDSS',
)
