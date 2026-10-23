"""Systemd user service manager for OMM Linux background auto-switching daemon."""

import os
import subprocess
from pathlib import Path
from typing import Tuple

SERVICE_NAME = "omm-linux-watcher.service"
OLD_SERVICE_NAME = "logitech-omm-watcher.service"


class BackgroundServiceManager:
    """Manages the omm-linux-watcher systemd user service."""

    @staticmethod
    def get_service_file_path() -> Path:
        return Path.home() / ".config" / "systemd" / "user" / SERVICE_NAME

    @staticmethod
    def ensure_service_installed() -> bool:
        """Installs or updates the systemd user service unit file and cleans up legacy service."""
        old_service_path = Path.home() / ".config" / "systemd" / "user" / OLD_SERVICE_NAME
        if old_service_path.exists():
            try:
                subprocess.run(["systemctl", "--user", "stop", OLD_SERVICE_NAME], capture_output=True, timeout=5)
                subprocess.run(["systemctl", "--user", "disable", OLD_SERVICE_NAME], capture_output=True, timeout=5)
                old_service_path.unlink(missing_ok=True)
            except Exception:
                pass

        service_path = BackgroundServiceManager.get_service_file_path()
        service_path.parent.mkdir(parents=True, exist_ok=True)

        appimage_path = "%h/Applications/OMM Linux"

        unit_content = f"""[Unit]
Description=OMM Linux Profile Auto-Switching Watcher
After=graphical-session.target

[Service]
Type=simple
ExecStart="{appimage_path}" --daemon
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
"""
        try:
            service_path.write_text(unit_content, encoding="utf-8")
            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    @staticmethod
    def is_running() -> bool:
        """Checks if the background service is currently active."""
        try:
            res = subprocess.run(
                ["systemctl", "--user", "is-active", SERVICE_NAME],
                capture_output=True,
                text=True,
                timeout=3,
            )
            return res.stdout.strip() == "active"
        except Exception:
            return False

    @staticmethod
    def is_enabled() -> bool:
        """Checks if the background service is enabled to start on boot/login."""
        try:
            res = subprocess.run(
                ["systemctl", "--user", "is-enabled", SERVICE_NAME],
                capture_output=True,
                text=True,
                timeout=3,
            )
            return res.stdout.strip() == "enabled"
        except Exception:
            return False

    @staticmethod
    def start() -> Tuple[bool, str]:
        BackgroundServiceManager.ensure_service_installed()
        try:
            res = subprocess.run(
                ["systemctl", "--user", "start", SERVICE_NAME],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                return True, "Background service started."
            return False, res.stderr.strip() or "Failed to start service"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def stop() -> Tuple[bool, str]:
        try:
            res = subprocess.run(
                ["systemctl", "--user", "stop", SERVICE_NAME],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                return True, "Background service stopped."
            return False, res.stderr.strip() or "Failed to stop service"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def set_autostart(enable: bool) -> Tuple[bool, str]:
        BackgroundServiceManager.ensure_service_installed()
        action = "enable" if enable else "disable"
        try:
            res = subprocess.run(
                ["systemctl", "--user", action, SERVICE_NAME],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                status_str = "enabled on boot/login" if enable else "disabled on boot/login"
                return True, f"Background service {status_str}."
            return False, res.stderr.strip() or f"Failed to {action} service"
        except Exception as e:
            return False, str(e)
