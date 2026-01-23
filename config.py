# Copyright (c) 2026 Jeff Nedley
# Licensed under the MIT License (see LICENSE for details)

import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Config paths
CONFIG_DIR = os.path.join(os.getenv('APPDATA'), 'AmpliFiTeleport')
os.makedirs(CONFIG_DIR, exist_ok=True)
UUID_FILE = os.path.join(CONFIG_DIR, 'teleport_uuid')
TOKEN_FILE = os.path.join(CONFIG_DIR, 'teleport_token_0')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'teleport.conf')

# WireGuard CLI path
WG_EXE = r'C:\Program Files\WireGuard\wireguard.exe'

def get_icon_path():
    """Get path to tray-icon.ico at runtime (bundled or development)."""
    if getattr(sys, 'frozen', False):  # Running as bundled .exe
        # Path to data files in PyInstaller's temp extraction folder
        base_path = sys._MEIPASS
    else:
        # Running as script
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, "tray-icon.ico")

ICON_PATH = get_icon_path()