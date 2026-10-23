"""Systemd user service manager for OMM background auto-switching daemon."""

import os
import subprocess
from pathlib import Path

SERVICE_NAME = "omm-watcher.service"
LEGACY_SERVICES = ["omm-linux-watcher.service", "logitech-omm-watcher.service"]


class BackgroundServiceManager:
    """Manages the omm-watcher systemd user service."""

    @staticmethod
    def get_service_file_path() -> Path:
        return Path.home() / ".config" / "systemd" / "user" / SERVICE_NAME

    @staticmethod
    def ensure_service_installed() -> bool:
        """Installs or updates the systemd user service unit file and cleans up legacy services."""
        for old_svc in LEGACY_SERVICES:
            old_service_path = Path.home() / ".config" / "systemd" / "user" / old_svc
            if old_service_path.exists():
                try:
                    subprocess.run(
                        ["systemctl", "--user", "stop", old_svc],
                        capture_output=True,
                        timeout=5,
                    )
                    subprocess.run(
                        ["systemctl", "--user", "disable", old_svc],
                        capture_output=True,
                        timeout=5,
                    )
                    old_service_path.unlink(missing_ok=True)
                except Exception:
                    pass

        service_path = BackgroundServiceManager.get_service_file_path()
        service_path.parent.mkdir(parents=True, exist_ok=True)

        appimage = Path.home() / "Applications" / "OMM"
        if not appimage.exists():
            appimage_alt = Path.home() / "Applications" / "OMM Linux"
            if appimage_alt.exists():
                appimage = appimage_alt

        if appimage.is_file() and os.access(appimage, os.X_OK):
            exec_start = f'"{appimage}" --daemon'
        else:
            exec_start = '"%h/.local/bin/omm" --daemon'

        unit_content = f"""[Unit]
Description=OMM Profile Auto-Switching Watcher
After=graphical-session.target

[Service]
Type=simple
ExecStart={exec_start}
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
"""
        try:
            if service_path.exists():
                existing = service_path.read_text(encoding="utf-8")
                if existing == unit_content:
                    return True
            service_path.write_text(unit_content, encoding="utf-8")
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"], capture_output=True, timeout=5
            )
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
    def start() -> tuple[bool, str]:
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
    def stop() -> tuple[bool, str]:
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
    def set_autostart(enable: bool) -> tuple[bool, str]:
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
                status_str = (
                    "enabled on boot/login" if enable else "disabled on boot/login"
                )
                return True, f"Background service {status_str}."
            return False, res.stderr.strip() or f"Failed to {action} service"
        except Exception as e:
            return False, str(e)
