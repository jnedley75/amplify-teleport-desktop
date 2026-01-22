# tray_app.py
import asyncio
import logging
import os
import sys
import subprocess
import time
import ctypes
import customtkinter as ctk
import pystray
from PIL import Image
import tkinter as tk
from tkinter import simpledialog, messagebox, Text, Toplevel, Scrollbar, END, ttk
from teleport import connect_device, get_device_token, generate_client_hint
from win11toast import toast
import threading
from plyer import notification

# Config paths
CONFIG_DIR = os.path.join(os.getenv('APPDATA'), 'AmpliFiTeleportForDesktop')
os.makedirs(CONFIG_DIR, exist_ok=True)
UUID_FILE = os.path.join(CONFIG_DIR, 'teleport_uuid')
TOKEN_FILE = os.path.join(CONFIG_DIR, 'teleport_token_0')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'teleport.conf')  # Fixed name for consistent tunnel name 'teleport'

# WireGuard CLI path
WG_EXE = 'C:\\Program Files\\WireGuard\\wireguard.exe'

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

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_elevated():
    """Relaunch as admin if not already."""
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)

def generate_config(pin=None):
    """Generate configuration for Wireguard tunnel to Amplifi Teleport"""
    try:
        if pin:
            # Generate or load UUID
            if os.path.exists(UUID_FILE):
                with open(UUID_FILE, 'r') as f:
                    client_hint = f.read().strip()
            else:
                client_hint = generate_client_hint()
                with open(UUID_FILE, 'w') as f:
                    f.write(client_hint)
            device_token = get_device_token(client_hint, pin)
            with open(TOKEN_FILE, 'w') as f:
                f.write(device_token)
        else:
            if not os.path.exists(TOKEN_FILE):
                raise Exception("No previous token found. Please enter a new PIN.")
            with open(TOKEN_FILE, 'r') as f:
                device_token = f.read().strip()
        config_str = connect_device(device_token)
        with open(CONFIG_PATH, 'w') as f:
            f.write(config_str)
        return True, config_str
    except Exception as e:
        return False, str(e)

def activate_tunnel():
    """Activate (or update) the tunnel: uninstall if exists, then install new."""
    if not os.path.exists(CONFIG_PATH):
        return False, "No config found. Generate one first."
    try:
        # Uninstall existing if present (ignore error if not)
        subprocess.run([WG_EXE, '/uninstalltunnelservice', 'teleport'], capture_output=True)
        # Install/activate
        subprocess.run([WG_EXE, '/installtunnelservice', CONFIG_PATH], check=True, capture_output=True)
        return True, "Tunnel activated!"
    except subprocess.CalledProcessError as e:
        return False, f"Activation failed: {e.stderr.decode()}"

def deactivate_tunnel():
    """Uninstall the Wireguard tunnel to deactivate the Amplifi Teleport connection."""
    try:
        subprocess.run([WG_EXE, '/uninstalltunnelservice', 'teleport'], check=True, capture_output=True)
        
        # Poll until service is gone or stopped
        max_wait = 8.0
        poll_interval = 0.8
        elapsed = 0.0
        while elapsed < max_wait:
            if not is_tunnel_active():
                return True, "Tunnel deactivated!"
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        return True, "Tunnel deactivation requested (status may take a moment to update)"
    except subprocess.CalledProcessError as e:
        if 'not found' in e.stderr.decode().lower():
            return False, "Tunnel not active."
        return False, f"Deactivation failed: {e.stderr.decode()}"
    
def is_tunnel_active(retries=3, delay=1.0):
    """Check if the 'teleport' tunnel service is running."""
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ['sc', 'query', 'WireGuardTunnel$teleport'],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout.lower()

            if result.returncode == 0:
                if 'running' in output:
                    return True
                if 'stopped' in output or '1  stopped' in output:
                    return False
                return False  # pending or unknown

            return False  # service not found

        except (subprocess.TimeoutExpired, FileNotFoundError):
            logging.warning("Could not query service")
            return False
        except Exception as e:
            logging.warning(f"Tunnel check failed: {str(e)}")
            return False

        # Retry after delay (helps catch post-uninstall lag)
        time.sleep(delay)

    return False  # After all retries, assume not active

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

def show_pin_dialog(and_activate=True):
    """Prompt for PIN using custom modern dialog, generate config, optionally activate."""
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

def on_connect(icon, item):
    """Checks if tunnel configuration exists. If not, prompts PIN dialog. If yes, prompts config refresh."""
    if not os.path.exists(TOKEN_FILE):
        try:
            show_pin_dialog(and_activate=True)
            return True, "Successfully Created New Connection"
        except Exception as e:
            return False, "Error Creating New Connection"
    else:
        return on_refresh_config(icon=None, item=None)

def on_disconnect(icon, item):
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

def open_options_window(icon=None, item=None):
    """Opens a modern CustomTkinter window with control buttons."""
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
            command=lambda: [icon.stop(), root.quit()],
            **button_style
        ).pack(pady=10)

    def action_and_refresh(action_func):
        success, msg = action_func(icon=None, item=None)

        time.sleep(1.0)

        refresh_buttons()

    refresh_buttons()
    root.mainloop()

def main():
    run_elevated()

    image = Image.open("tray-icon.ico")

    # Right-click menu (unchanged)
    menu = pystray.Menu(
        pystray.MenuItem("Connect", on_connect),
        pystray.MenuItem("Disconnect", on_disconnect),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Delete Existing Configuration", on_delete_config),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda: [icon.stop(), sys.exit(0)])
    )

    # Left-click opens the controls window
    icon = pystray.Icon(
        "AmpliFi Teleport",
        image,
        "AmpliFi Teleport for Desktop",
        menu=pystray.Menu(
            pystray.MenuItem("Open Controls", open_options_window, default=True, visible=False),
            *menu.items
        )
    )

    icon.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()