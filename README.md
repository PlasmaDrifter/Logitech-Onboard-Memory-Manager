# Logitech Onboard Memory Manager (Linux)

A native Linux GUI application designed to inspect, edit, and burn button assignments, DPI stages, and profiles directly into the onboard flash memory of Logitech gaming mice (such as the Logitech G502 X PLUS, G502 LIGHTSPEED, HERO, etc.).

No Windows, Logitech G HUB, or background services required.

---

## Key Features

- **Direct Hardware Onboard Memory Access**: Reads and writes directly to hardware flash sectors. Changes persist across all operating systems, computers, and reboots.
- **Physical Button Mapping**: Remap all 11 physical mouse buttons:
  - Standard Mouse Clicks (Left, Right, Middle, Back, Forward, Extra buttons)
  - Keyboard Shortcuts (Interactive recorder capturing any key with Ctrl, Shift, Alt, Super modifiers)
  - Mouse Functions (DPI Shift/Sniper, Next DPI, Prev DPI, Cycle DPI, Profile Switch, Wheel Tilts)
  - Disabled / No Action
- **G-Shift Mode Support**: Configure secondary button behaviors when G-Shift is active.
- **DPI Stages & Polling Rates**: Customize up to 5 DPI sensitivity stages per profile and adjust reporting rates (1000 Hz, 500 Hz, etc.).
- **Multi-Profile Management**: Supports all 5 onboard hardware profile slots.
- **Automated Backup & Safety**: Automatically writes a timestamped YAML backup before flashing any sector changes.
- **Zero-Install / Fresh Machine Ready**: Can be run directly from source or compiled into a single self-contained portable executable.

---

## Quick Start

### Running Directly from Source
```bash
cd ~/Source/logitech-onboard-gui
./main.py
```

### Desktop Integration (KDE / GNOME Menu)
To add a launcher to your application menu:
```bash
cd ~/Source/logitech-onboard-gui
./install.sh
```
This adds `logitech-onboard-gui` to your `PATH` and registers the application in your desktop application menu.

### Building a Standalone Single-File Executable
To generate a single portable binary that runs on any fresh Linux machine with zero setup:
```bash
cd ~/Source/logitech-onboard-gui
./build_standalone.sh
```
The resulting binary will be located in `dist/logitech-onboard-gui`.

---

## Hardware Permissions (udev)

On modern Linux distributions utilizing systemd and `uaccess`, standard input devices are accessible to logged-in desktop users without root. 

If running on a minimal or custom Linux installation where `/dev/hidraw*` is restricted to root, add this standard udev rule:

`/etc/udev/rules.d/99-logitech-hidraw.rules`:
```udev
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="046d", TAG+="uaccess"
```
Reload rules:
```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```
