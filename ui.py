# Copyright (c) 2026 Jeff Nedley
# Licensed under the MIT License (see LICENSE for details)

import os
import time
import logging
import sys

import customtkinter as ctk

from config import TOKEN_FILE, UUID_FILE, CONFIG_PATH, ICON_PATH
from tunnel import generate_config, activate_tunnel, deactivate_tunnel, is_tunnel_active
from notifications import show_toast

logger = logging.getLogger("AmpliFi Teleport for Desktop")

def custom_pin_dialog():
    """Custom PIN input dialog with centered label"""
    dialog = ctk.CTkToplevel()
    dialog.title("Teleport PIN Entry")
    dialog.geometry("350x180")
    dialog.resizable(False, False)
    dialog.configure(fg_color="#181818")
    dialog.iconbitmap(ICON_PATH)
    
    # Delete after customtkinter v5.3.0 comes out
    dialog.after(300, lambda: dialog.iconbitmap(ICON_PATH))
    
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    dialog.grab_set()
    dialog.focus_set()

    ctk.CTkLabel(
        dialog,
        text="Enter Teleport PIN",
        font=("Arial", 16, "bold"),
        text_color="white"
    ).pack(pady=(20, 5))

    def validate(P):
        if len(P) > 5:
            return False
        return True

    vcmd = (dialog.register(validate), '%P')

    pin_entry = ctk.CTkEntry(
        dialog,
        width=280,
        height=40,
        font=("Arial", 16),
        fg_color="#2d2d2d",
        text_color="white",
        justify="center",
        validate="key",
        validatecommand=vcmd
    )
    pin_entry.pack(pady=(0, 15))
    pin_entry.focus()

    result = [None]

    def submit():
        pin = pin_entry.get().strip()
        if len(pin) != 5:
            ctk.CTkLabel(dialog, text="PIN must be exactly 5 characters", text_color="red").pack(pady=5)
            return
        result[0] = pin
        dialog.destroy()

    def cancel():
        result[0] = None
        dialog.destroy()

    button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    button_frame.pack(pady=10)

    ctk.CTkButton(
        button_frame,
        text="Cancel",
        width=120,
        fg_color="#444444",
        hover_color="#555555",
        text_color="white",
        command=cancel
    ).pack(side="left", padx=10)

    ctk.CTkButton(
        button_frame,
        text="Submit",
        width=120,
        fg_color="#1a9aff",
        hover_color="#0d6efd",
        text_color="white",
        command=submit
    ).pack(side="right", padx=10)

    dialog.wait_window()
    return result[0]

def custom_confirm_dialog(title, message):
    """Custom confirmation dialog"""
    confirm_dialog = ctk.CTkToplevel()
    confirm_dialog.title(title)
    confirm_dialog.geometry("350x180")
    confirm_dialog.resizable(False, False)
    confirm_dialog.configure(fg_color="#181818")
    confirm_dialog.iconbitmap(ICON_PATH)
    
    # Delete after customtkinter v5.3.0 comes out
    confirm_dialog.after(300, lambda: confirm_dialog.iconbitmap(ICON_PATH))
    
    confirm_dialog.update_idletasks()
    width = confirm_dialog.winfo_width()
    height = confirm_dialog.winfo_height()
    x = (confirm_dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (confirm_dialog.winfo_screenheight() // 2) - (height // 2)
    confirm_dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    confirm_dialog.grab_set()
    confirm_dialog.focus_set()

    ctk.CTkLabel(
        confirm_dialog,
        text=message,
        font=("Arial", 14),
        text_color="white",
        wraplength=300
    ).pack(pady=20)

    button_frame = ctk.CTkFrame(confirm_dialog, fg_color="transparent")
    button_frame.pack(pady=10)

    result = [False]

    def yes():
        result[0] = True
        confirm_dialog.destroy()

    def no():
        result[0] = False
        confirm_dialog.destroy()

    ctk.CTkButton(
        button_frame,
        text="No",
        width=120,
        fg_color="#444444",
        hover_color="#555555",
        text_color="white",
        command=no
    ).pack(side="left", padx=10)

    ctk.CTkButton(
        button_frame,
        text="Yes",
        width=120,
        fg_color="#1a9aff",
        hover_color="#0d6efd",
        text_color="white",
        command=yes
    ).pack(side="right", padx=10)

    confirm_dialog.wait_window()
    return result[0]

def open_options_window(icon=None, item=None):
    """Opens a modern CustomTkinter window with control buttons."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("AmpliFi Teleport for Desktop")
    root.geometry("350x320")
    root.resizable(False, False)
    root.configure(bg="#181818")
    root.iconbitmap(ICON_PATH)
    
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    header_frame = ctk.CTkFrame(root, fg_color="#1a9aff", corner_radius=0)
    header_frame.pack(fill="x", pady=(0, 10))

    header_label = ctk.CTkLabel(
        header_frame,
        text="AmpliFi Teleport for Desktop",
        font=("Arial", 18, "bold"),
        text_color="white"
    )
    header_label.pack(pady=12)

    content_frame = ctk.CTkFrame(root, fg_color="transparent")
    content_frame.pack(fill="both", expand=True, padx=20, pady=10)
    
    ctk.CTkLabel(
        root,
        text="Version 1.0.0",
        font=("Arial", 10),
        text_color="#888888"
    ).pack(side="bottom", pady=(0, 10))

    def refresh_buttons():
        for widget in content_frame.winfo_children():
            widget.destroy()

        tunnel_active = is_tunnel_active(retries=4, delay=0.8)

        button_style = {
            "width": 280,
            "height": 50,
            "corner_radius": 20,
            "text_color": "white",
            "font": ("Arial", 14, "bold")
        }

        if not tunnel_active:
            ctk.CTkButton(
                content_frame,
                text="Connect",
                fg_color="#1a9aff",
                hover_color="#0d6efd",
                command=lambda: action_and_refresh(on_connect),
                **button_style
            ).pack(pady=10)

        if tunnel_active:
            ctk.CTkButton(
                content_frame,
                text="Disconnect",
                fg_color="#1a9aff",
                hover_color="#0d6efd",
                command=lambda: action_and_refresh(on_disconnect),
                **button_style
            ).pack(pady=10)

        if os.path.exists(TOKEN_FILE) or os.path.exists(UUID_FILE) or os.path.exists(CONFIG_PATH):
            ctk.CTkButton(
                content_frame,
                text="Delete Existing Configuration",
                fg_color="#1a9aff",
                hover_color="#0d6efd",
                command=lambda: action_and_refresh(on_delete_config),
                **button_style
            ).pack(pady=10)

        ctk.CTkButton(
            content_frame,
            text="Quit",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=lambda: [sys.exit(0)],
            **button_style
        ).pack(pady=10)

    def action_and_refresh(action_func):
        success, msg = action_func(icon=None, item=None)

        time.sleep(1.5)

        refresh_buttons()

    refresh_buttons()
    root.mainloop()
    
    
def show_pin_dialog(and_activate=True):
    pin = custom_pin_dialog()
    if not pin or pin.strip() == "":
        return False, "No PIN entered."

    success, msg = generate_config(pin)
    if not success:
        return False, msg

    if and_activate:
        act_success, act_msg = activate_tunnel()
        if act_success:
            show_toast("Status Update", "Teleport connected!")
            return True, "Tunnel connected successfully"
        else:
            return False, act_msg
    else:
        show_toast("Config Update", "Teleport configuration updated!")
        return True, "Config generated successfully"

def on_refresh_config(icon, item):
    if not os.path.exists(TOKEN_FILE):
        show_toast("Error", "No previous configuration. Enter a PIN first.")
        return
    success, msg = generate_config(pin=None)
    if success:
        act_success, act_msg = activate_tunnel()
        show_toast("Status Update", "Teleport connected!")
        return act_success, act_msg
    else:
        logger.error("Error While Refreshing Configuration for a New Connection", exc_info=True)
        show_toast("Error", f"Refresh failed: {msg}")
        return success, msg

def on_connect(icon, item):
    if not os.path.exists(TOKEN_FILE):
        try:
            show_pin_dialog(and_activate=True)
            return True, "Successfully Created New Connection"
        except Exception as e:
            logger.error("Error While Creating a New Connection", exc_info=True)
            return False, "Error Creating New Connection"
    else:
        return on_refresh_config(icon=None, item=None)

def on_disconnect(icon, item):
    if not is_tunnel_active():
        show_toast("Error", "No Teleport Tunnel is active")
        return False, "No Teleport Tunnel is active"
    else:
        success, msg = deactivate_tunnel()
        show_toast("Status Update", "Teleport disconnected!")
        return success, msg

def on_delete_config(icon, item):
    if custom_confirm_dialog("Confirm Deletion", "Delete previous Teleport configuration?"):
        try:
            logger.debug("Disregard following deactivation error if any")
            deactivate_tunnel()
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
            if os.path.exists(UUID_FILE):
                os.remove(UUID_FILE)
            if os.path.exists(CONFIG_PATH):
                os.remove(CONFIG_PATH)
            show_toast("Config Update", "Existing configuration deleted!")
            return True, "Configuration Deleted"
        except Exception as e:
            logger.error("Error While Deleting Existing Configuration", exc_info=True)
            show_toast("Error", f"Deletion failed: {str(e)}")
            return False, "Error while deleting configuration"