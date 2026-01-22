import asyncio
import logging
import os
import sys
import subprocess
import time
import ctypes
import customtkinter as ctk
import pystray
import tkinter as tk
from tkinter import simpledialog, messagebox, Text, Toplevel, Scrollbar, END, ttk
from win11toast import toast
import threading
from plyer import notification
from PIL import Image

import customtkinter as ctk
from plyer import notification

from teleportSetup import generate_config, activate_tunnel, deactivate_tunnel, is_tunnel_active

def show_toast(title, message, icon_path="tray-icon.ico"):
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="AmpliFi Teleport for Desktop",
            app_icon=icon_path,
            timeout=5,  # seconds
            ticker="Notification"
        )
    except Exception as e:
        logging.error(f"Plyer toast failed: {e}")

def show_pin_dialog(and_activate=True, configs=[None]):
    """Prompt for PIN using custom modern dialog, generate config, optionally activate."""
    pin = custom_pin_dialog()

    if not pin or pin.strip() == "":
        return False, "No PIN entered."

    success, msg = generate_config(pin=pin, configs=configs)
    if not success:
        return False, msg

    if and_activate:
        act_success, act_msg = activate_tunnel(configs=configs)
        if act_success:
            show_toast("Status Update", "Teleport connected!")
            return True, "Tunnel connected successfully"
        else:
            messagebox.showerror("Error", act_msg)
            return False, act_msg
    else:
        show_toast("Config Update", "Teleport configuration updated!")
        return True, "Config generated successfully"

def on_refresh_config(icon, item):
    """Refresh Wireguard tunnel configuration using existing token. Then activates connection"""
    if not os.path.exists(TOKEN_FILE):
        messagebox.showerror("Error", "No previous configuration. Enter a PIN first.")
        return
    success, msg = generate_config(pin=None)
    if success:
        act_success, act_msg = activate_tunnel()
        show_toast("Status Update", "Teleport connected!")
        return act_success, act_msg
    else:
        messagebox.showerror("Error", f"Refresh failed: {msg}")
        return success, msg

def on_connect(configs=[None]):
    """Checks if tunnel configuration exists. If not, prompts PIN dialog. If yes, prompts config refresh."""
    print("NOW IN HERE")
    CONFIG_PATH = configs[0]
    TOKEN_FILE = configs[1]
    UUID_FILE = configs[2]
    
    if not os.path.exists(TOKEN_FILE):
        try:
            show_pin_dialog(and_activate=True, configs=configs)
            return True, "Successfully Created New Connection"
        except Exception as e:
            return False, "Error Creating New Connection"
    else:
        return on_refresh_config(icon=None, item=None)

def on_disconnect(configs=[None]):
    """Checks if tunnel is active. If yes, prompts tunnel deactivation."""
    if not is_tunnel_active:
        messagebox.showerror("Error", "No Teleport Tunnel is active")
        return False, "No Teleport Tunnel is active"
    else:
        success, msg = deactivate_tunnel()
        show_toast("Status Update", "Teleport disconnected!")
        return success, msg

def on_delete_config(icon, item):
    """Confirms with user to delete configs. If yes, shuts down tunnel (if needed) and deletes all config files"""
    if custom_confirm_dialog("Confirm Deletion", "Delete previous Teleport configuration?"):
        try:
            deactivate_tunnel()  # Ignore result
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
            if os.path.exists(UUID_FILE):
                os.remove(UUID_FILE)
            if os.path.exists(CONFIG_PATH):
                os.remove(CONFIG_PATH)
            show_toast("Config Update", "Existing configuration deleted!")
            return True, "Configuration Deleted"
        except Exception as e:
            messagebox.showerror("Error", f"Deletion failed: {str(e)}")
            return False, "Error while deleting configuration"