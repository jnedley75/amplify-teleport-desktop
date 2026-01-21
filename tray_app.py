# tray_app.py
import asyncio
import logging
import os
import sys
import subprocess
import time
import ctypes
import pystray
from PIL import Image
import tkinter as tk
from tkinter import simpledialog, messagebox, Text, Toplevel, Scrollbar, END
from teleport import connect_device, get_device_token, generate_client_hint

# Config paths (store in appdata to persist)
CONFIG_DIR = os.path.join(os.getenv('APPDATA'), 'AmpliFiTeleport')
os.makedirs(CONFIG_DIR, exist_ok=True)
UUID_FILE = os.path.join(CONFIG_DIR, 'teleport_uuid')
TOKEN_FILE = os.path.join(CONFIG_DIR, 'teleport_token_0')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'teleport.conf')  # Fixed name for consistent tunnel name 'teleport'

# WireGuard CLI path (assume in PATH; or set full path e.g., r'C:\Program Files\WireGuard\wireguard.exe')
WG_EXE = 'wireguard.exe'

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
    """Mirror original main.py logic to generate WireGuard config."""
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
    """Check if the 'teleport' tunnel service is running (active)."""
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

        # If we got here, retry after delay (helps catch post-uninstall lag)
        time.sleep(delay)

    return False  # After all retries, assume not active

def show_pin_dialog(and_activate=True):
    """Prompt for PIN, generate config, optionally activate."""
    root = tk.Tk()
    root.withdraw()
    pin = simpledialog.askstring("AmpliFi Teleport", "Enter your Teleport PIN (e.g., AB123):")
    root.destroy()
    if pin:
        success, msg = generate_config(pin)
        if success:
            if and_activate:
                act_success, act_msg = activate_tunnel()
                messagebox.showinfo("Result", act_msg if act_success else f"Error: {act_msg}")
            else:
                messagebox.showinfo("Result", "Config generated successfully!")
        else:
            messagebox.showerror("Error", f"Generation failed: {msg}")

def on_refresh_config(icon, item):
    if not os.path.exists(TOKEN_FILE):
        messagebox.showerror("Error", "No previous configuration. Enter a PIN first.")
        return
    success, msg = generate_config(pin=None)
    if success:
        act_success, act_msg = activate_tunnel()
        messagebox.showinfo("Result", act_msg if act_success else f"Error: {act_msg}")
        return act_success, act_msg
    else:
        messagebox.showerror("Error", f"Refresh failed: {msg}")
        return success, msg

def on_connect(icon, item):
    if not os.path.exists(TOKEN_FILE):
        try:
            show_pin_dialog(and_activate=True)
            return True, "Successfully Created New Connection"
        except Exception as e:
            return False, "Error Creating New Connection"
    else:
        return on_refresh_config(icon=None, item=None)

def on_disconnect(icon, item):
    if not is_tunnel_active:
        messagebox.showerror("Error", "No Teleport Tunnel is active")
        return False, "No Teleport Tunnel is active"
    else:
        success, msg = deactivate_tunnel()
        messagebox.showinfo("Tunnel", msg if success else f"Error: {msg}")
        return success, msg

def on_delete_config(icon, item):
    if messagebox.askyesno("Confirm", "Delete previous configuration and reset?"):
        try:
            deactivate_tunnel()  # Ignore result
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
            if os.path.exists(UUID_FILE):
                os.remove(UUID_FILE)
            if os.path.exists(CONFIG_PATH):
                os.remove(CONFIG_PATH)
            messagebox.showinfo("Deleted", "Configuration deleted. You can now enter a new PIN.")
            return True, "Configuration Deleted"
        except Exception as e:
            messagebox.showerror("Error", f"Deletion failed: {str(e)}")
            return False, "Error while deleting configuration"

def open_options_window(icon=None, item=None):
    """Opens a Tkinter window with dynamic, refreshable buttons."""
    root = tk.Tk()
    root.title("AmpliFi Teleport Controls")
    root.geometry("300x220")
    root.resizable(False, False)
    root.attributes('-topmost', True)  # Keep on top

    # Header
    tk.Label(root, text="AmpliFi Teleport", font=("Arial", 14, "bold")).pack(pady=10)

    # Container frame for buttons (we'll clear and repopulate this)
    button_frame = tk.Frame(root)
    button_frame.pack(fill='both', expand=True, padx=20, pady=10)

    def refresh_buttons():
        # Clear existing buttons
        for widget in button_frame.winfo_children():
            widget.destroy()

        tunnel_active = is_tunnel_active(retries=4, delay=0.8)

        if not tunnel_active:
            # Show Connect when inactive or no tunnel
            tk.Button(
                button_frame,
                text="Connect",
                width=25,
                command=lambda: action_and_refresh(on_connect)
            ).pack(pady=8)

        if tunnel_active:
            # Show Disconnect only when tunnel is active
            tk.Button(
                button_frame,
                text="Disconnect",
                width=25,
                command=lambda: action_and_refresh(on_disconnect)
            ).pack(pady=8)

        if os.path.exists(TOKEN_FILE) or os.path.exists(UUID_FILE) or os.path.exists(CONFIG_PATH):
            tk.Button(
                button_frame,
                text="Delete Existing Configuration",
                width=25,
                command=lambda: action_and_refresh(on_delete_config)
            ).pack(pady=8)

        tk.Button(
            button_frame,
            text="Quit",
            width=25,
            command=lambda: sys.exit(0)
        ).pack(pady=8)

    def action_and_refresh(action_func):
        """Run the action, show result if needed, then refresh buttons."""
        # Run the original action (pass None for icon/item since not needed here)
        success, msg = action_func(icon=None, item=None)

        # Refresh the button layout immediately after action
        refresh_buttons()

    # Initial population of buttons
    refresh_buttons()

    root.mainloop()

def main():
    run_elevated()  # Keep admin elevation

    # Removed: no auto-PIN prompt or connection on launch
    # User must left-click tray icon → open window → click Connect to trigger PIN if needed

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
        "AmpliFi Teleport Tray",
        menu=pystray.Menu(
            pystray.MenuItem("Open Controls", open_options_window, default=True, visible=False),
            *menu.items
        )
    )

    icon.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()