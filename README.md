# Logitech Onboard Memory Manager (Linux)

A native Linux GUI application designed to inspect, edit, and write button assignments, DPI stages, and profiles directly into the onboard flash memory of Logitech gaming mice (such as the Logitech G502 X PLUS, G502 LIGHTSPEED, HERO, and other HID++ 2.0 compatible hardware).

No Windows installation, Logitech G HUB, Solaar, or background daemons required.

---

## Features

- **Direct Hardware Onboard Memory Access**: Communicates directly over `/dev/hidraw*` via raw HID++ 2.0 protocol (`0x8100` Onboard Profiles feature). Edits are burned straight into the mouse flash sectors and persist across computers, operating systems, and reboots.
- **Physical Button Remapping**:
  - Standard Mouse Buttons (Left, Right, Middle, Back, Forward, Extra buttons)
  - Keyboard Shortcuts (Interactive recorder capturing single keys or complex combos with Ctrl, Shift, Alt, and Super modifiers)
  - Hardware Functions (DPI Shift/Sniper, Next DPI, Previous DPI, Cycle DPI, Profile Switch, Wheel Tilt Left/Right)
  - Disabled / No Action
- **G-Shift Support**: Configure distinct secondary button bindings for G-Shift mode.
- **DPI Profiles & Polling Rate**: Adjust up to 5 DPI sensitivity stages per profile and set report rates (125 Hz, 250 Hz, 500 Hz, 1000 Hz).
- **Multi-Profile Management**: Supports all 5 onboard hardware profile slots with direct active profile switching.
- **Lighting Controls**: Includes hardware RGB shutoff and an automatic toggle to disable RGB lighting on save.
- **Automated Backups**: Automatically generates timestamped YAML backups of all onboard memory sectors before committing changes.
- **Zero Dependencies via AppImage**: Single executable format that runs out of the box on any modern Linux distribution.

---

## Download & Installation

### Option 1: AppImage (Recommended)

Download the latest standalone executable from the [Releases](https://github.com/PlasmaDrifter/Logitech-Onboard-Memory-Manager/releases) page:

```bash
chmod +x Logitech-Onboard-Memory-Manager-x86_64.AppImage
./Logitech-Onboard-Memory-Manager-x86_64.AppImage
```

### Option 2: Running from Source

Requirements: Python 3.10+ and PySide6 (`pip install PySide6 pyyaml`).

```bash
git clone https://github.com/PlasmaDrifter/Logitech-Onboard-Memory-Manager.git
cd Logitech-Onboard-Memory-Manager
./main.py
```

### Option 3: Desktop Menu Integration

To integrate into your KDE Plasma or GNOME desktop launcher:

```bash
./install.sh
```

This creates a symlink in `~/.local/bin/logitech-onboard-gui`, installs the application icon, and adds the `.desktop` launcher.

---

## Building

### Building the AppImage
```bash
./build_appimage.sh
```
The output file will be generated in `dist/Logitech-Onboard-Memory-Manager-x86_64.AppImage`.

### Building a Standalone Binary
```bash
./build_standalone.sh
```
The single-file binary will be generated in `dist/logitech-onboard-gui`.

---

## Hardware Permissions (udev)

Standard Linux distributions running systemd automatically grant access to user input devices (`/dev/hidraw*`) via `uaccess`.

If running on a minimal or restricted system where non-root access to `/dev/hidraw*` is blocked, install this udev rule:

`/etc/udev/rules.d/99-logitech-hidraw.rules`:
```udev
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="046d", TAG+="uaccess"
```

Reload rules:
```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

---

## License

MIT License.
