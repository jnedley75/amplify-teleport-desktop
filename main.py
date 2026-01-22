import asyncio
import logging
import os
import sys
import subprocess
import time
import ctypes
import pystray
from PIL import Image

from config import CONFIG_PATH, TOKEN_FILE, UUID_FILE, WG_EXE
from tunnel import generate_config, activate_tunnel, deactivate_tunnel, is_tunnel_active
from ui import custom_pin_dialog, custom_confirm_dialog, open_options_window
from notifications import show_toast

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_elevated():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)

def main():
    run_elevated()

    image = Image.open("tray-icon.ico")

    menu = pystray.Menu(
        pystray.MenuItem("Quit", lambda: [icon.stop(), sys.exit(0)])
    )

    icon = pystray.Icon(
        "AmpliFi Teleport",
        image,
        "AmpliFi Teleport for Desktop",
        menu=pystray.Menu(
            pystray.MenuItem("Open Controls", lambda: open_options_window(icon), default=True, visible=False),
            *menu.items
        )
    )

    icon.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()