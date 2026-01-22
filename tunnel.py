import subprocess
import time
import logging
import os

from config import WG_EXE, CONFIG_PATH, TOKEN_FILE, UUID_FILE
from teleport import connect_device, get_device_token, generate_client_hint

def generate_config(pin=None):
    """Generate configuration for Wireguard tunnel to Amplifi Teleport"""
    try:
        if pin:
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
        subprocess.run([WG_EXE, '/uninstalltunnelservice', 'teleport'], capture_output=True)
        subprocess.run([WG_EXE, '/installtunnelservice', CONFIG_PATH], check=True, capture_output=True)
        return True, "Tunnel activated!"
    except subprocess.CalledProcessError as e:
        return False, f"Activation failed: {e.stderr.decode()}"

def deactivate_tunnel():
    """Uninstall the Wireguard tunnel to deactivate the Amplifi Teleport connection."""
    try:
        subprocess.run([WG_EXE, '/uninstalltunnelservice', 'teleport'], check=True, capture_output=True)
        
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
                return False

            return False

        except (subprocess.TimeoutExpired, FileNotFoundError):
            logging.warning("Could not query service")
            return False
        except Exception as e:
            logging.warning(f"Tunnel check failed: {str(e)}")
            return False

        time.sleep(delay)

    return False