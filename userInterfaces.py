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

from teleportSetup import is_tunnel_active
from userCrudOps import on_connect, on_disconnect, on_delete_config

def custom_pin_dialog():
    """Custom PIN input dialog with label"""
    dialog = ctk.CTkToplevel()
    dialog.title("Teleport PIN Entry")
    dialog.geometry("350x180")
    dialog.resizable(False, False)
    dialog.configure(fg_color="#181818")
    
    # Center the dialog on screen
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    dialog.grab_set()
    dialog.focus_set()

    # Header label
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

    # PIN Textbox
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

    # Buttons row
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

    def submit():
        pin = pin_entry.get().strip().upper()
        if len(pin) != 5:  # Optional: enforce exactly 5 chars
            messagebox.showwarning("Invalid PIN", "PIN must be exactly 5 characters.")
            return
        result[0] = pin
        dialog.destroy()

    def cancel():
        result[0] = None
        dialog.destroy()

    # Buttons row
    button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    button_frame.pack(pady=15)

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
    """Custom Confirm input dialog with label."""
    # Custom confirmation dialog
    confirm_dialog = ctk.CTkToplevel()
    confirm_dialog.title(title)
    confirm_dialog.geometry("350x180")
    confirm_dialog.resizable(False, False)
    confirm_dialog.configure(fg_color="#181818")
    
     # Center the dialog on screen
    confirm_dialog.update_idletasks()
    width = confirm_dialog.winfo_width()
    height = confirm_dialog.winfo_height()
    x = (confirm_dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (confirm_dialog.winfo_screenheight() // 2) - (height // 2)
    confirm_dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    confirm_dialog.grab_set()
    confirm_dialog.focus_set()

    # Header Label
    ctk.CTkLabel(
        confirm_dialog,
        text=message,
        font=("Arial", 14),
        text_color="white",
        wraplength=300
    ).pack(pady=20)

    button_frame = ctk.CTkFrame(confirm_dialog, fg_color="transparent")
    button_frame.pack(pady=10)

    result = [False]  # [confirm yes/no]

    def yes():
        result[0] = True
        confirm_dialog.destroy()

    def no():
        result[0] = False
        confirm_dialog.destroy()
        
    # Buttons Row
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

def open_options_window(configs=[None, None, None]):
    """Opens a modern CustomTkinter window with control buttons."""
    CONFIG_PATH = configs[0]
    TOKEN_FILE = configs[1]
    UUID_FILE = configs[2]
    
    ctk.set_appearance_mode("dark")  # Matches your #181818 dark theme
    ctk.set_default_color_theme("blue")  # Base theme - can be "green", "dark-blue", etc.

    root = ctk.CTk()
    root.title("AmpliFi Teleport for Desktop")
    root.geometry("350x320")
    root.resizable(False, False)
    root.configure(bg="#181818")
    
    # Center on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    # Header frame 
    header_frame = ctk.CTkFrame(root, fg_color="#1a9aff", corner_radius=0)
    header_frame.pack(fill="x", pady=(0, 10))

    header_label = ctk.CTkLabel(
        header_frame,
        text="AmpliFi Teleport for Desktop",
        font=("Arial", 18, "bold"),
        text_color="white"
    )
    header_label.pack(pady=12)

    # Main content frame
    content_frame = ctk.CTkFrame(root, fg_color="transparent")
    content_frame.pack(fill="both", expand=True, padx=20, pady=10)
    
     # Version label
    ctk.CTkLabel(
        root,
        text="Version 1.0.0",
        font=("Arial", 10),
        text_color="#888888"
    ).pack(side="bottom", pady=(0, 10))

    def refresh_buttons():
        # Clear previous buttons
        for widget in content_frame.winfo_children():
            widget.destroy()

        tunnel_active = is_tunnel_active(retries=4, delay=0.8)

        # Custom button style with gradient-like hover
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
                command=lambda: action_and_refresh(on_connect, configs=configs),
                **button_style
            ).pack(pady=10)

        if tunnel_active:
            ctk.CTkButton(
                content_frame,
                text="Disconnect",
                fg_color="#1a9aff",
                hover_color="#0d6efd",
                command=lambda: action_and_refresh(on_disconnect, configs=configs),
                **button_style
            ).pack(pady=10)

        if os.path.exists(TOKEN_FILE) or os.path.exists(UUID_FILE) or os.path.exists(CONFIG_PATH):
            ctk.CTkButton(
                content_frame,
                text="Delete Existing Configuration",
                fg_color="#1a9aff",
                hover_color="#0d6efd",
                command=lambda: action_and_refresh(on_delete_config, configs=configs),
                **button_style
            ).pack(pady=10)

        ctk.CTkButton(
            content_frame,
            text="Quit",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=lambda: [root.quit()],
            **button_style
        ).pack(pady=10)

    def action_and_refresh(action_func, configs=[None]):
        print("IN HERE")
        success, msg = action_func(configs=configs)

        time.sleep(1.0)

        refresh_buttons()

    refresh_buttons()
    root.mainloop()