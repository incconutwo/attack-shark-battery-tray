# Changelog

All notable changes to the Mouse Battery Tray project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v1.2.0] - 2026-07-24

### 🚀 Major Highlights

- **Multi-Brand Mouse Support:** Expanded beyond Attack Shark X11 to support **WLMouse Beast X** series, **Pulsar** series, **VXE R1** series, andgeneric Beken/CompX OEM dongles.
- **Modular Codebase Architecture:** Completely refactored the legacy monolithic script into maintainable modules (`config.py`, `devices.py`, `icon_drawer.py`, `updater.py`, `battery_tray.pyw`).
- **Windows Taskbar Light/Dark Mode Support:** Automatic real-time taskbar theme detection with optimized icon contrast for both Light and Dark Windows themes.
- **Intelligent Battery Remaining Time Estimation:** Real-time discharge rate tracking with tooltip estimates (e.g. `~12h 30m`), complete with sleep/idle gap filtering.
- **Low Battery Toast Notifications:** Native Windows toast alerts triggered when battery level crosses customizable thresholds (25%, 20%, 15%, 10%, or Disabled).

---

### ✨ New Features

- **WLMouse Protocol Engine (`devices.py`):** Added active HID feature report polling (`0x83` query) and passive heartbeat packet parsing for WLMouse Beast X & Beast X Mini Pro (8K receiver support).
- **Expanded Device Database:** Mapped hardware product IDs for:
  - Attack Shark: X11, X11 Pro, X11 SE, X6, X3, R1
  - Pulsar: Xlite Wireless, 8K Dongle Gen.2
  - VXE: R1 / R1 SE / R1 SE+ (CompX/Evision/Zikway dongles)
- **Automatic Update Checker (`updater.py`):** Asynchronous GitHub release checking with semver comparison. Users can check manually or receive background prompts when updates are published.
- **Single Instance Guard (`config.py`):** Named Windows Mutex (`MouseBatteryTray_SingleInstance_Mutex`) prevents multiple app instances from running simultaneously.
- **Memory & RAM Optimization:** Added periodic Python garbage collection (`gc.collect()`), Windows working set trimming (`SetProcessWorkingSetSize`), and Image/Font handle caching.
- **Enhanced Tray Visual Indicators:** Distinct visual states:
  - `Chg` (Blue): Battery charging / wired connection
  - `--` (Grey): Connected, awaiting initial status packet
  - `??` (Grey): Disconnected / Receiver unplugged
  - `?` (Purple): Device detected, battery reading unsupported

---

### 🛠 Refactoring & Internal Improvements

- **Renamed Main Entrypoint:** Transitioned from `x11_battery_tray.pyw` to `battery_tray.pyw` for universal branding.
- **Registry Management (`config.py`):** Native Windows registry persistence (`HKCU\Software\MouseBatteryTray`) for user settings (alert threshold, hours estimate toggle) without requiring administrator rights.
- **Zero-UAC Windows Autostart:** Clean startup key registration (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`) supporting both Python interpreter runs and frozen executables.
- **Thread-Safe Architecture:** Background HID polling, UI event loop, and HTTP update checks run on separate threads.

---

### 📦 Build & Hardware Extraction Tools

- **PyInstaller Build Spec (`MouseBatteryTray.spec`):** Added standalone `.exe` build configuration.
- **Hardware ID Extractor Wizard (`dump_devices.py`):** Interactive 2-step prompt for users to capture wireless and wired HID payloads for easy community device submissions.

---

### 📚 Documentation

- **Updated README.md:** Included comprehensive compatibility matrix, step-by-step installation instructions, troubleshooting tips, and contributor guidance.
