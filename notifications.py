from plyer import notification
import logging

def show_toast(title, message, icon_path="tray-icon.ico"):
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="AmpliFi Teleport for Desktop",
            app_icon=icon_path,
            timeout=5,
            ticker="Notification"
        )
    except Exception as e:
        logging.error(f"Plyer toast failed: {e}")