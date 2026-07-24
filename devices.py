import time
import hid
from typing import Optional, Tuple, List

# =============================================================================
# Supported Standard Devices (Beken, CompX, Pulsar, etc.)
# =============================================================================
SUPPORTED_VIDS = {0x1d57, 0x25a7, 0x3710, 0x258a, 0x0c45, 0x093a, 0x24ae, 0x1bcf, 0x3554, 0x320f, 0x3537}

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

    # VXE R1 Series (R1 / R1 SE / R1 SE+)
    (0x3554, 0xf58e): ("VXE R1 Series", "wireless"),
    (0x320f, 0x5055): ("VXE R1 Series", "wireless"),
    (0x3537, 0x2106): ("VXE R1 Series", "wireless"),
    0xf58e: ("VXE R1 Series", "wireless"),
    0x5055: ("VXE R1 Series", "wireless"),
    0x2106: ("VXE R1 Series", "wireless"),
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


def find_device_path() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Scan HID devices for standard supported mice."""
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
