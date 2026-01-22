import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Config paths
CONFIG_DIR = os.path.join(os.getenv('APPDATA'), 'AmpliFiTeleport')
os.makedirs(CONFIG_DIR, exist_ok=True)
UUID_FILE = os.path.join(CONFIG_DIR, 'teleport_uuid')
TOKEN_FILE = os.path.join(CONFIG_DIR, 'teleport_token_0')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'teleport.conf')

# WireGuard CLI path
WG_EXE = r'C:\Program Files\WireGuard\wireguard.exe'