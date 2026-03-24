# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for La Mia Scribe — cross-platform build."""

import sys
import os

block_cipher = None
ROOT = os.path.abspath(os.path.dirname(SPEC))

a = Analysis(
    [os.path.join(ROOT, 'main.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'assets'), 'assets'),
    ],
    hiddenimports=[
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'faster_whisper',
        'ctranslate2',
        'yt_dlp',
        'ollama',
        'reportlab',
        'reportlab.lib',
        'reportlab.lib.pagesizes',
        'reportlab.pdfgen',
        'reportlab.platypus',
        'docx',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == 'darwin':
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='LaMiaScribe',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        icon=os.path.join(ROOT, 'assets', 'AppIcon.icns'),
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        name='LaMiaScribe',
    )
    app = BUNDLE(
        coll,
        name='La Mia Scribe.app',
        icon=os.path.join(ROOT, 'assets', 'AppIcon.icns'),
        bundle_identifier='pro.techinclusion.lamiascribe',
        info_plist={
            'CFBundleName': 'La Mia Scribe',
            'CFBundleDisplayName': 'La Mia Scribe',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': True,
            'NSMicrophoneUsageDescription': 'La Mia Scribe needs microphone access for live transcription.',
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='LaMiaScribe',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        icon=os.path.join(ROOT, 'assets', 'logo.png') if sys.platform != 'win32'
             else os.path.join(ROOT, 'assets', 'logo.png'),
    )
