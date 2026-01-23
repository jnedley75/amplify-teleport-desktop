# Copyright (c) 2026 Jeff Nedley
# Licensed under the MIT License (see LICENSE for details)

from plyer import notification
import logging

from config import ICON_PATH

logger = logging.getLogger("AmpliFi Teleport for Desktop")

def show_toast(title, message, icon_path=None):
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="AmpliFi Teleport for Desktop",
            app_icon=ICON_PATH,
            timeout=5,
            ticker="Notification"
        )
    except Exception as e:
        logger.error("Error while creating Windows 11 Toast Notification", exc_info=True)