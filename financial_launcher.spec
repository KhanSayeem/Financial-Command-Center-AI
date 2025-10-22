# -*- mode: python ; coding: utf-8 -*-



block_cipher = None



a = Analysis(

    ['financial_launcher.py'],

    pathex=[],

    binaries=[],

    datas=[

        ('requirements.txt', '.'),

        ('launcher_requirements.txt', '.'),

        ('README.md', '.'),

    ],

    hiddenimports=[

        'PIL._tkinter_finder',

        'tkinter',

        'tkinter.ttk',

        'pystray._win32',

        'requests.packages.urllib3',

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



exe = EXE(

    pyz,

    a.scripts,

    a.binaries,

    a.zipfiles,

    a.datas,

    [],

    name='Financial-Command-Center-Launcher',

    debug=False,

    bootloader_ignore_signals=False,

    strip=False,

    upx=True,

    upx_exclude=[],

    runtime_tmpdir=None,

    console=False,

    disable_windowed_traceback=False,

    target_arch=None,

    codesign_identity=None,

    entitlements_file=None,

    icon='assets/application.ico',

    version='version.txt',

)

