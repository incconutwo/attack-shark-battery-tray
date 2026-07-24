import sys
import os
import gc
import ctypes
import winreg

# Registry Keys & Constants
REG_SETTINGS_KEY = r"Software\MouseBatteryTray"
MUTEX_NAME = "MouseBatteryTray_SingleInstance_Mutex"
ERROR_ALREADY_EXISTS = 183

_mutex_handle = None


def trim_memory():
    """Run Python garbage collection and trim the process working set on Windows."""
    gc.collect()
    try:
        ctypes.windll.kernel32.SetProcessWorkingSetSize(
            ctypes.windll.kernel32.GetCurrentProcess(),
            -1, -1
        )
    except Exception:
        pass


def acquire_single_instance() -> bool:
    """Ensure only one instance of Mouse Battery Tray is running at a time."""
    global _mutex_handle
    try:
        _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if not _mutex_handle:
            return False
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            ctypes.windll.kernel32.CloseHandle(_mutex_handle)
            _mutex_handle = None
            return False
        return True
    except Exception:
        return True


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


def get_alert_threshold() -> int:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SETTINGS_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, "AlertThreshold")
            return int(val)
    except (FileNotFoundError, OSError, ValueError):
        return 20  # Default 20%


def set_alert_threshold(threshold: int) -> bool:
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_SETTINGS_KEY) as key:
            winreg.SetValueEx(key, "AlertThreshold", 0, winreg.REG_DWORD, int(threshold))
        return True
    except Exception as e:
        print(f"Error saving alert threshold: {e}")
        return False


def get_show_estimate() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SETTINGS_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, "ShowEstimate")
            return bool(val)
    except (FileNotFoundError, OSError, ValueError):
        return True  # Enabled by default


def set_show_estimate(enabled: bool) -> bool:
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_SETTINGS_KEY) as key:
            winreg.SetValueEx(key, "ShowEstimate", 0, winreg.REG_DWORD, 1 if enabled else 0)
        return True
    except Exception as e:
        print(f"Error saving estimate setting: {e}")
        return False


def is_light_mode() -> bool:
    """Detect if Windows taskbar/system theme is set to Light Mode."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            0,
            winreg.KEY_READ
        ) as key:
            val, _ = winreg.QueryValueEx(key, "SystemUsesLightTheme")
            return val == 1
    except (FileNotFoundError, OSError, ValueError):
        return False


def get_battery_history() -> tuple:
    """Load persisted (history_list, is_anchored) from Windows Registry."""
    import json
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SETTINGS_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, "BatteryHistory")
            anchored_val, _ = winreg.QueryValueEx(key, "BatteryAnchored")
            raw_list = json.loads(val)
            parsed = [(float(t), int(b)) for t, b in raw_list if isinstance(t, (int, float)) and isinstance(b, int)]
            return parsed, bool(anchored_val)
    except Exception:
        return [], False


def set_battery_history(history: list, is_anchored: bool) -> bool:
    """Save battery history and estimate anchor state to Windows Registry."""
    import json
    try:
        data = json.dumps(history)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_SETTINGS_KEY) as key:
            winreg.SetValueEx(key, "BatteryHistory", 0, winreg.REG_SZ, data)
            winreg.SetValueEx(key, "BatteryAnchored", 0, winreg.REG_DWORD, 1 if is_anchored else 0)
        return True
    except Exception as e:
        print(f"Error saving battery history: {e}")
        return False

