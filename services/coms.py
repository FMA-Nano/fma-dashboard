"""COM / serial device service.

Migrated to remote execution: /dev/ttyUSB*, /dev/ttyACM*, udevadm, and
/proc/device-tree/model all describe the Nano's hardware, so device
discovery + identification now runs on the Nano over SSH as a single
bundled script (one round trip instead of one per device), and the
result is parsed back into the same ComDevice/ComStatus objects the
screens already expect.

Board-type caching (BOARD_TYPE) is kept on the laptop side across calls,
same as before, just populated from the remote board_type value now.
"""

import json

from services.remote import run_remote

BOARD_TYPE = None

BOARD_MAPPING = {

    "NanoPC-T3": {
        "FC": "3",
        "DET": "4",
        "ATG": "1",
    },

    "NanoPC-T4": {
        "FC": "2",
        "DET": "6",
        "ATG": "3",
    },

    "NanoPC-T6": {
        "FC": "1",
    },
}


class ComDevice:
    def __init__(self):
        self.device = ""
        self.type = ""
        self.driver = ""
        self.vendor = ""
        self.model = ""
        self.serial = ""
        self.path = ""
        self.usb_port = ""
        self.name = ""
        self.connected = False


class ComStatus:
    def __init__(self):
        self.devices = []
        self.total = 0


# This script runs *on the Nano*. It enumerates ttyUSB*/ttyACM* devices,
# queries udevadm for each, and reports the board model - all in one SSH
# round trip. USB-port parsing and device naming (which needs the board
# type + BOARD_MAPPING) is done back on the laptop, since that mapping is
# dashboard configuration rather than something the Nano needs to know.
_DEVICES_REMOTE_SCRIPT = r"""
import glob, json, subprocess

def board_model():
    try:
        with open("/proc/device-tree/model") as f:
            return f.read().replace("\x00", "")
    except Exception:
        return ""

def device_info(device):
    info = {"device": device, "vendor": "", "model": "", "serial": "",
            "path": "", "driver": "", "devpath": ""}

    if device.startswith("/dev/ttyUSB"):
        info["type"] = "USB Serial"
    elif device.startswith("/dev/ttyACM"):
        info["type"] = "USB ACM"
    else:
        info["type"] = ""

    try:
        result = subprocess.run(
            ["udevadm", "info", "--query=property", "--name", device],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key == "ID_VENDOR":
                info["vendor"] = value
            elif key == "ID_MODEL":
                info["model"] = value
            elif key == "ID_SERIAL_SHORT":
                info["serial"] = value
            elif key == "ID_PATH":
                info["path"] = value
            elif key == "ID_USB_DRIVER":
                info["driver"] = value
            elif key == "DEVPATH":
                info["devpath"] = value
    except Exception:
        pass

    return info

devices = []
for pattern in ("/dev/ttyUSB*", "/dev/ttyACM*"):
    devices.extend(glob.glob(pattern))

result = {
    "board_model": board_model(),
    "devices": [device_info(d) for d in devices],
}

print(json.dumps(result))
"""


def get_devices():

    status = ComStatus()

    result = run_remote(["python3", "-c", _DEVICES_REMOTE_SCRIPT], timeout=10)

    if not result.ok:
        return status

    try:
        payload = json.loads(result.stdout)
    except Exception:
        return status

    _set_board_type_from_model(payload.get("board_model", ""))

    for info in payload.get("devices", []):
        com = ComDevice()
        com.device = info.get("device", "")
        com.type = info.get("type", "")
        com.driver = info.get("driver", "")
        com.vendor = info.get("vendor", "")
        com.model = info.get("model", "")
        com.serial = info.get("serial", "")
        com.path = info.get("path", "")
        com.connected = True
        com.usb_port = get_usb_port(info.get("devpath", ""))
        com.name = identify_device(com.usb_port)
        status.devices.append(com)

    status.total = len(status.devices)

    return status


def get_device(device):
    """Fetch info for a single device path. Kept for interface
    compatibility; internally just filters a full get_devices() call
    since discovery is already bundled into one remote round trip.
    """
    for com in get_devices().devices:
        if com.device == device:
            return com
    return None


def run_command(command):
    result = run_remote(command, timeout=5)
    return result.stdout if result.ok else ""


_ATG_READ_SCRIPT = r"""
import sys
try:
    import serial
except ImportError:
    print("PYSERIAL_MISSING")
    sys.exit(0)

try:
    ser = serial.Serial('/dev/ttyS4', 19200, timeout=2.5)
    data = ser.read(256)
    ser.close()
    print("DATA" if data else "NODATA")
except Exception as e:
    print("ERROR:%s" % e)
"""


def get_atg_status():
    """Check whether the ATG (tank gauge) is actively sending data on
    its serial line.

    Uses a bounded pyserial read (timeout=2.5s) rather than `cat`, which
    blocks indefinitely waiting for any byte and has no clean way to say
    "nothing arrived in time" - it just gets killed by the outer SSH
    timeout, which is unreliable and tends to under-report as
    "Not Found" even when the device is actually connected and working.

    This still isn't perfect - if the ATG only transmits less often than
    every ~2.5s, a single check can still miss it - but it's
    substantially more reliable than the blocking-cat approach. A truly
    reliable fix would be a small persistent reader running on the Nano
    that keeps the port open continuously; this is a lighter-weight
    improvement in the meantime.
    """

    result = run_remote(["sudo", "python3", "-c", _ATG_READ_SCRIPT], timeout=8)

    if not result.ok and result.error_kind in ("offline", "timeout", "auth", "not_found"):
        return result.status_word()

    output = result.stdout.strip()

    if output == "DATA":
        return "Connected"

    if output == "PYSERIAL_MISSING":
        return "pyserial Not Installed"

    if output.startswith("ERROR:"):
        return "Not Found"

    return "Not Found"


def get_usb_port(devpath):

    board = get_board_type()

    # NanoPC-T3
    # Example:
    # 2-1.3
    # 2-1.4

    if board == "NanoPC-T3":

        parts = devpath.split("/")

        for part in parts:

            if "." in part and "-" in part:

                return part.split(".")[-1]

    # NanoPC-T4
    # Example:
    # usb6/6-1
    # usb2/2-1

    elif board == "NanoPC-T4":

        parts = devpath.split("/")

        for part in parts:

            if part.startswith("usb"):

                return part.replace("usb", "")

    return ""


def _set_board_type_from_model(model):
    global BOARD_TYPE

    if "NanoPC-T3" in model:
        BOARD_TYPE = "NanoPC-T3"
    elif "NanoPC-T4" in model:
        BOARD_TYPE = "NanoPC-T4"
    elif "NanoPC-T6" in model:
        BOARD_TYPE = "NanoPC-T6"
    else:
        BOARD_TYPE = "Unknown"

    return BOARD_TYPE


def get_board_type():

    global BOARD_TYPE

    # Already detected this session, return saved value
    if BOARD_TYPE:
        return BOARD_TYPE

    result = run_remote(["cat", "/proc/device-tree/model"], timeout=5)

    if not result.ok:
        BOARD_TYPE = "Unknown"
        return BOARD_TYPE

    return _set_board_type_from_model(result.stdout)


def identify_device(port):

    board = get_board_type()

    mapping = BOARD_MAPPING.get(board, {})

    for name, usb_port in mapping.items():

        if port == usb_port:
            return name

    return "Unknown"


def get_device_status(devices, name):

    for device in devices:

        if device.name == name:
            return "Connected"

    return "Not Found"


if __name__ == "__main__":

    print("Board:")
    print(get_board_type())

    print()

    devices = get_devices()

    for device in devices.devices:

        print("--------------------------------")
        print("Device:", device.device)
        print("Name:", device.name)
        print("Port:", device.usb_port)
        print("Vendor:", device.vendor)
        print("Model:", device.model)
        print("Serial:", device.serial)
