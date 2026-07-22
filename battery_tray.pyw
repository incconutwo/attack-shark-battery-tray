import sys
import os
import time
import threading
from typing import Optional, Tuple, List

import hid
from PIL import Image, ImageDraw, ImageFont
import pystray
import winreg

# =============================================================================
# Supported Standard Devices (Beken, CompX, Pulsar, etc.)
# =============================================================================
SUPPORTED_VIDS = {0x1d57, 0x25a7, 0x3710, 0x258a, 0x0c45, 0x093a, 0x24ae, 0x1bcf}

SUPPORTED_DEVICES = {
    # Attack Shark X11
    (0x1d57, 0xfa60): ("Attack Shark X11", "wireless"),
    (0x1d57, 0xfa55): ("Attack Shark X11", "wired"),
    0xfa60: ("Attack Shark X11", "wireless"),
    0xfa55: ("Attack Shark X11", "wired"),
    
    # Attack Shark R1
    (0x1d57, 0xfa61): ("Attack Shark R1", "wired"),
    0xfa61: ("Attack Shark R1", "wired"),
    
    # Attack Shark X3
    (0x1d57, 0xfa50): ("Attack Shark X3", "wired"),
    0xfa50: ("Attack Shark X3", "wired"),
    
    # Attack Shark X6
    (0x1d57, 0xfa62): ("Attack Shark X6", "wireless"),
    (0x1d57, 0xfa56): ("Attack Shark X6", "wired"),
    0xfa62: ("Attack Shark X6", "wireless"),
    0xfa56: ("Attack Shark X6", "wired"),

    # Pulsar Xlite Wireless
    (0x25a7, 0xfa7c): ("Pulsar Xlite Wireless", "wireless"),
    (0x25a7, 0xfa7b): ("Pulsar Xlite Wireless", "wired"),
    0xfa7c: ("Pulsar Xlite Wireless", "wireless"),
    0xfa7b: ("Pulsar Xlite Wireless", "wired"),

    # Pulsar 8K Dongle Gen.2
    (0x3710, 0x5406): ("Pulsar 8K Dongle Gen.2", "wireless"),
    0x5406: ("Pulsar 8K Dongle Gen.2", "wireless"),
}

# =============================================================================
# WLMouse Beast X family
# =============================================================================
WLMOUSE_VID = 0x36a7

WLMOUSE_DEVICES = {
    0xa887: "WLMouse Beast X",
    0xa868: "WLMouse Beast X Mini Pro",
}

WLMOUSE_QUERY = [0x00, 0x00, 0x02, 0x02, 0x00, 0x83]


# =============================================================================
# Registry Helpers
# =============================================================================
def is_startup_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, "MouseBatteryTray")
            return True
    except (FileNotFoundError, OSError):
        return False


def set_startup(enabled: bool) -> bool:
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    name = "MouseBatteryTray"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
            if enabled:
                if getattr(sys, 'frozen', False):
                    cmd = f'"{sys.executable}"'
                else:
                    script_path = os.path.abspath(sys.argv[0])
                    pythonw_path = sys.executable.replace("python.exe", "pythonw.exe")
                    cmd = f'"{pythonw_path}" "{script_path}"'
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"Error setting registry startup: {e}")
        return False


# =============================================================================
# WLMouse Handlers
# =============================================================================
def _wlmouse_parse(resp: List[int]) -> Tuple[Optional[int], Optional[bool]]:
    """Parse a data reply 'a1 00 02 02 00 83 <charge> <batt>' -> (batt, charging)."""
    if not resp:
        return None, None
    for i in range(5, len(resp) - 2):
        if (resp[i] == 0x83 and resp[i - 1] == 0x00 and resp[i - 2] == 0x02
                and resp[i - 5] in (0xa1, 0xa2)):
            charge = resp[i + 1]
            batt = resp[i + 2]
            if 0 <= batt <= 100:
                return batt, bool(charge)
    return None, None


def _wlmouse_read_feature(path: str) -> Tuple[Optional[int], Optional[bool]]:
    """Active: replay the HUB's 0x83 read, poll the feature report for the reply."""
    try:
        dev = hid.device()
        dev.open_path(path.encode('utf-8') if isinstance(path, str) else path)
    except OSError:
        return None, None
    try:
        report = [0x00] + WLMOUSE_QUERY + [0x00] * (64 - len(WLMOUSE_QUERY))
        try:
            dev.send_feature_report(report)
        except OSError:
            pass
        for _ in range(15):
            time.sleep(0.05)
            for length in (65, 64):
                try:
                    resp = dev.get_feature_report(0, length)
                except OSError:
                    resp = None
                if resp:
                    batt, charging = _wlmouse_parse(list(resp))
                    if batt is not None:
                        return batt, charging
        return None, None
    finally:
        try:
            dev.close()
        except Exception:
            pass


def _wlmouse_read_passive(path: str, seconds: float = 6.0) -> Tuple[Optional[int], Optional[bool]]:
    """Fallback: catch the '03 00 <batt> <charge>' heartbeat. No writes at all."""
    try:
        dev = hid.device()
        dev.open_path(path.encode('utf-8') if isinstance(path, str) else path)
        dev.set_nonblocking(True)
    except OSError:
        return None, None
    deadline = time.time() + seconds
    try:
        while time.time() < deadline:
            try:
                data = dev.read(64)
            except OSError:
                break
            if data:
                d = list(data)
                for off in (0, 1):
                    if len(d) >= off + 4 and d[off] == 0x03 and d[off + 1] == 0x00:
                        batt = d[off + 2]
                        if 0 <= batt <= 100:
                            return batt, bool(d[off + 3])
            time.sleep(0.02)
    finally:
        try:
            dev.close()
        except Exception:
            pass
    return None, None


def find_wlmouse() -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """Return (path, model_name, pid) for the WLMouse feature interface."""
    fallback = None
    for d in hid.enumerate(WLMOUSE_VID):
        pid = d['product_id']
        name = WLMOUSE_DEVICES.get(pid) or d.get('product_string') or "WLMouse Device"
        if d.get('usage_page') == 0xffff and d.get('usage') == 0x00:
            return d['path'], name, pid
        if d.get('usage_page') == 0xffff and fallback is None:
            fallback = (d['path'], name, pid)
    return fallback if fallback else (None, None, None)


def read_wlmouse_battery(path: str) -> Tuple[Optional[int], Optional[bool]]:
    """Return (battery%, charging) or (None, None)."""
    batt, charging = _wlmouse_read_feature(path)
    if batt is not None:
        return batt, charging
    for d in hid.enumerate(WLMOUSE_VID):
        b, c = _wlmouse_read_passive(d['path'], seconds=4.0)
        if b is not None:
            return b, c
    return None, None


# =============================================================================
# Tray Application
# =============================================================================
class BatteryTrayApp:
    def __init__(self):
        self.icon = None
        self.running = True
        self.last_battery = -1
        self.status = "disconnected"
        self.charging = False
        self.current_model = "Mouse"
        
        self.poll_thread = threading.Thread(target=self.poll_loop, daemon=True)
        
    def create_image(self, text: str, text_color: Tuple[int, int, int]) -> Image.Image:
        width, height = 64, 64
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        font = None
        try:
            font = ImageFont.truetype("arialbd.ttf", 54 if len(text) <= 2 else 34)
        except OSError:
            try:
                font = ImageFont.truetype("arial.ttf", 54 if len(text) <= 2 else 34)
            except OSError:
                font = ImageFont.load_default()
            
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        text_width = right - left
        text_height = bottom - top
        
        x = (width - text_width) / 2 - left
        y = (height - text_height) / 2 - top
            
        draw.text((x, y), text, fill=text_color, font=font)
        return image

    def get_icon_data(self) -> Image.Image:
        if self.status == "disconnected":
            return self.create_image("??", (150, 150, 150))
        elif self.status == "charging" and self.last_battery < 0:
            return self.create_image("Chg", (52, 152, 219))
        elif self.status == "unknown":
            return self.create_image("?", (155, 89, 182))
        else:
            pct = self.last_battery
            if self.status == "charging":
                color = (52, 152, 219)
            elif pct >= 50:
                color = (46, 204, 113)
            elif pct >= 20:
                color = (230, 126, 34)
            else:
                color = (231, 76, 60)
            return self.create_image(str(pct), color)

    def update_tray(self):
        if not self.icon:
            return
        
        self.icon.icon = self.get_icon_data()
        
        model = self.current_model or "Mouse"
        if self.status == "disconnected":
            self.icon.title = f"{model}: Disconnected"
        elif self.status == "charging" and self.last_battery < 0:
            self.icon.title = f"{model}: Charging/Wired"
        elif self.status == "charging":
            self.icon.title = f"{model}: {self.last_battery}% (charging)"
        elif self.status == "unknown":
            self.icon.title = f"{model}: detected (battery unavailable)"
        else:
            self.icon.title = f"{model}: {self.last_battery}%"

    def find_device_path(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        for d in hid.enumerate():
            vid = d['vendor_id']
            pid = d['product_id']
            if vid in SUPPORTED_VIDS and d['interface_number'] == 2 and d['usage_page'] == 10:
                if (vid, pid) in SUPPORTED_DEVICES:
                    model_name, mode = SUPPORTED_DEVICES[(vid, pid)]
                    return d['path'], mode, model_name
                elif pid in SUPPORTED_DEVICES:
                    model_name, mode = SUPPORTED_DEVICES[pid]
                    return d['path'], mode, model_name
                
                prod_string = str(d.get('product_string', '')).lower()
                if "wired" in prod_string:
                    mode = "wired"
                elif "wireless" in prod_string or "receiver" in prod_string or "dongle" in prod_string:
                    mode = "wireless"
                else:
                    mode = "wireless"
                
                model_name = d.get('product_string', 'Gaming Mouse')
                if model_name in ['2.4G Wireless Device', '2.4G Receiver']:
                    model_name = "Wireless Mouse"
                return d['path'], mode, model_name
                
        return None, None, None

    def poll_loop(self):
        while self.running:
            path, mode, model_name = self.find_device_path()
            if path:
                self._handle_standard_device(path, mode, model_name)
                continue
                
            wl_path, wl_name, wl_pid = find_wlmouse()
            if wl_path:
                self.current_model = wl_name
                battery, charging = read_wlmouse_battery(wl_path)
                if battery is not None:
                    self.last_battery = battery
                    self.charging = bool(charging)
                    self.status = "charging" if charging else "connected"
                else:
                    self.status = "unknown"
                self.update_tray()
                time.sleep(10)
                continue
                
            if self.status != "disconnected":
                self.status = "disconnected"
                self.update_tray()
            time.sleep(5)

    def _handle_standard_device(self, path: str, mode: str, model_name: str):
        self.current_model = model_name
        if mode == "wired":
            if self.status != "charging":
                self.status = "charging"
                self.update_tray()
            time.sleep(5)
            return
            
        try:
            dev = hid.device()
            dev.open_path(path.encode('utf-8') if isinstance(path, str) else path)
            dev.set_nonblocking(True)
            
            if self.status in ("disconnected", "charging", "unknown"):
                self.status = "connected"
                if self.last_battery == -1:
                    self.last_battery = 100
                self.update_tray()
            
            last_recv_time = time.time()
            while self.running:
                if time.time() - last_recv_time > 5:
                    path_check, mode_check, model_check = self.find_device_path()
                    if not path_check or mode_check != "wireless":
                        break
                    self.current_model = model_check
                    last_recv_time = time.time()
                    
                try:
                    data = dev.read(64)
                    if data:
                        if len(data) >= 5 and data[0] == 0x03 and data[1] == 0x55 and data[2] == 0x40 and data[3] == 0x01:
                            battery = data[4]
                            if 0 <= battery <= 100:
                                self.last_battery = battery
                                self.status = "connected"
                                self.update_tray()
                                last_recv_time = time.time()
                    time.sleep(0.1)
                except OSError:
                    break
                    
            dev.close()
        except OSError:
            self.status = "disconnected"
            self.update_tray()
            time.sleep(5)
        finally:
            try:
                dev.close()
            except Exception:
                pass

    def on_exit(self, icon, item):
        self.running = False
        self.icon.stop()

    def toggle_startup(self, icon, item):
        new_state = not item.checked
        set_startup(new_state)

    def run(self):
        menu = pystray.Menu(
            pystray.MenuItem("Start with Windows", self.toggle_startup, checked=lambda item: is_startup_enabled()),
            pystray.MenuItem("Exit", self.on_exit)
        )
        self.icon = pystray.Icon(
            "Mouse Battery Tray",
            self.get_icon_data(),
            "Mouse Battery Tray: Initializing...",
            menu
        )
        
        self.poll_thread.start()
        self.icon.run()


if __name__ == "__main__":
    app = BatteryTrayApp()
    app.run()
