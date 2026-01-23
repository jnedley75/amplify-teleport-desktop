# Copyright (c) 2026 Jeff Nedley
# Licensed under the MIT License (see LICENSE for details)

import asyncio
import logging
import os
import sys
import subprocess
import time
import ctypes
import pystray
from PIL import Image
from logging.handlers import RotatingFileHandler

from config import CONFIG_PATH, TOKEN_FILE, UUID_FILE, WG_EXE, ICON_PATH
from tunnel import generate_config, activate_tunnel, deactivate_tunnel, is_tunnel_active
from ui import custom_pin_dialog, custom_confirm_dialog, open_options_window
from notifications import show_toast

logger = logging.getLogger("AmpliFi Teleport for Desktop")
logger.setLevel(logging.DEBUG)

# File handler
file_handler = RotatingFileHandler(
    "amplifi_teleport.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
))

logger.addHandler(file_handler)

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

    image = Image.open(ICON_PATH)

    menu = pystray.Menu(
        pystray.MenuItem("Quit", lambda: [sys.exit(0)])
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
    
    logger.info("Application started!")
    open_options_window(icon)
    
    icon.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()