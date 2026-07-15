# Attack Shark Mouse Battery Tray Indicator

<img src="https://github.com/user-attachments/assets/4e384838-6073-4457-827c-737c18f909f2" alt="Attack Shark Battery Tray Screenshot" width="150" align="right">

A lightweight, standalone Windows system tray application that displays the live battery percentage of Beken/Sino Wealth based wireless gaming mice (such as the Attack Shark X11, R1, X3, X6, etc.) directly in the taskbar.

This tool serves as a lightweight alternative to the official, resource-heavy manufacturer hub software.

---

## Features

- **Live Numeric Percentage:** Displays the exact battery level directly on the tray icon as a colored number.
- **Color-Coded Status:**
  - 🟢 **Green** ($\ge 50\%$) - Healthy charge
  - 🟠 **Orange** ($20\% - 49\%$) - Moderate charge
  - 🔴 **Red** ($< 20\%$) - Low battery (time to charge)
- **Charging Detection:** Automatically detects wired connection/charging state and displays **`Chg`** (in blue).
- **Offline Detection:** Displays **`??`** (in grey) if the mouse goes out of range or is switched off.
- **Start with Windows Toggle:** Right-click the icon to toggle startup behavior. It writes directly to your user registry (`HKCU`), requiring **zero Administrator (UAC) prompts**.
- **Universal Compatibility:** Works generically with any mouse using Beken-OEM firmware (`VID: 0x1d57`) and reads the device product string to show customized tooltips.
- **Ultralight:** Uses near-zero CPU and negligible RAM.

---

## Installation

### Prerequisites
Make sure you have [Python 3.10+](https://www.python.org/) installed and added to your system PATH.

### Install Dependencies
Open your terminal (Command Prompt or PowerShell) and run:
```bash
pip install hidapi pystray pillow
```

---

## How to Run

1. **Run in Background (Recommended):**
   Run the file using `pythonw` (or double-click the `.pyw` extension) to start it silently in the background:
   ```bash
   pythonw x11_battery_tray.pyw
   ```
2. **Run in Terminal (Debugging):**
   If you want to view console logs:
   ```bash
   python x11_battery_tray.pyw
   ```

---

## Troubleshooting

- **Icon Stays on `??`:** 
  Ensure the mouse is turned on, in wireless mode (using the 2.4G adapter), and not asleep. Wake the mouse by moving it around for the first battery status packet to transmit.
- **Permissions Issue:**
  The app runs entirely in user-space and does not require admin rights. If the tray icon doesn't update, check if another exclusive tool (like the official software) is currently open and locking the USB receiver port.

---

## Contributing/Adding New Models
If your mouse uses the same OEM framework but reports a different Product ID (PID), you can easily add it to the `SUPPORTED_DEVICES` dictionary at the top of `x11_battery_tray.pyw`:

```python
SUPPORTED_DEVICES = {
    # Add your custom mouse details here
    0xYOUR_PID_HEX: ("Your Mouse Name", "wireless"),
}
```

*To find your mouse's PID, open Windows Device Manager, find the mouse properties, and check under **Details > Hardware IDs**.*
