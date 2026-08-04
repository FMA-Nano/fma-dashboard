"""System status service.

Uses only the Python standard library - no third-party packages required.
(psutil would make CPU/RAM/disk collection simpler if it's ever available
on the NanoPC, but everything here is implemented against /proc and /sys
directly so there's nothing extra to install.)

Python 3.8 compatible: uses typing.Dict/Optional instead of the 3.9+/3.10+
builtin generic syntax (dict[...], str | None).
"""
import platform
import os
import subprocess
import time
from typing import Dict, Optional
import sqlite3

THERMAL_ZONE_PATH = "/sys/class/thermal/thermal_zone0/temp"
LOADAVG_PATH = "/proc/loadavg"
MEMINFO_PATH = "/proc/meminfo"
UPTIME_PATH = "/proc/uptime"
OS_RELEASE_PATH = "/etc/os-release"

SYSTEMCTL_TIMEOUT = 3

DATABASE = "/home/pi/ST500V3/Main/app.db"

def get_system_status() -> Dict[str, str]:

    return {

        # Nano
        "hostname": _get_hostname(),
        "firmware" : _get_firmware_version(),
        
        # Health
        "cpu": _get_cpu_percent(),
        "ram": _get_ram_percent(),
        "disk": _get_disk_percent(),
        "temperature": _get_temperature(),

        # Runtime
        "uptime": _get_uptime(),
        "load": _get_load_average(),

        # Software
        "kernel": _get_kernel_version(),
        "os": _get_os_name(),

        # Hardware
        "architecture": _get_architecture(),
        "cpu_model": _get_cpu_model(),
        "serial": _get_serial(),
    }



# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_systemctl(args) -> str:
    try:
        result = subprocess.run(
            ["systemctl"] + args,
            capture_output=True,
            text=True,
            timeout=SYSTEMCTL_TIMEOUT,
        )
        return result.stdout.strip()
    except FileNotFoundError:
        return "unknown"
    except subprocess.TimeoutExpired:
        return "unknown"
    except Exception:
        return "unknown"


def _get_cpu_percent() -> str:
    """Sample /proc/stat twice with a short delay to compute CPU usage.

    This avoids depending on psutil - it's the same technique psutil itself
    uses internally (a delta between two /proc/stat snapshots).
    """
    try:
        first = _read_cpu_times()
        time.sleep(0.1)
        second = _read_cpu_times()

        idle_delta = second[3] - first[3]
        total_delta = sum(second) - sum(first)

        if total_delta <= 0:
            return "Unknown"

        usage = 100.0 * (1.0 - (idle_delta / total_delta))
        return f"{usage:.0f}%"
    except Exception:
        return "Unknown"


def _read_cpu_times():
    with open("/proc/stat", "r") as f:
        line = f.readline()
    parts = line.split()
    # parts[0] == "cpu", followed by: user nice system idle iowait irq softirq ...
    return [int(x) for x in parts[1:8]]


def _get_ram_percent() -> str:
    try:
        values = {}
        with open(MEMINFO_PATH, "r") as f:
            for line in f:
                key, _, rest = line.partition(":")
                values[key.strip()] = int(rest.strip().split()[0])

        total = values.get("MemTotal")
        available = values.get("MemAvailable")

        if not total or available is None:
            return "Unknown"

        used_percent = 100.0 * (1 - (available / total))
        return f"{used_percent:.0f}%"
    except Exception:
        return "Unknown"


def _get_disk_percent() -> str:
    try:
        usage = os.statvfs("/")
        total = usage.f_blocks * usage.f_frsize
        free = usage.f_bfree * usage.f_frsize
        if total == 0:
            return "Unknown"
        used_percent = 100.0 * (1 - (free / total))
        return f"{used_percent:.0f}%"
    except Exception:
        return "Unknown"


def _get_temperature() -> str:
    try:
        with open(THERMAL_ZONE_PATH, "r") as f:
            raw = int(f.read().strip())
        celsius = raw / 1000.0
        return f"{celsius:.1f}\u00b0C"
    except Exception:
        return "Unknown"


def _get_uptime() -> str:
    try:
        with open(UPTIME_PATH, "r") as f:
            seconds = float(f.read().split()[0])

        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)

        if days >= 1:
            return f"{days} days"
        if hours >= 1:
            return f"{hours} hours"
        return f"{minutes} minutes"
    except Exception:
        return "Unknown"



def _get_firmware_version():

    try:

        conn = sqlite3.connect(DATABASE)

        cursor = conn.cursor()

        cursor.execute(
            "SELECT TypeString FROM config WHERE id = 3"
        )

        row = cursor.fetchone()

        conn.close()

        print("ROW =", row)

        if row is None:
            return "No Row Found"

        return row[0]

    except Exception as e:
        return f"ERROR: {e}"
    

def _get_load_average() -> str:
    try:
        with open(LOADAVG_PATH, "r") as f:
            parts = f.read().split()
        one, five, fifteen = parts[0], parts[1], parts[2]
        return f"{one}, {five}, {fifteen}"
    except Exception:
        return "Unknown"


def _get_kernel_version() -> str:
    try:
        result = subprocess.run(
            ["uname", "-r"], capture_output=True, text=True, timeout=SYSTEMCTL_TIMEOUT
        )
        version = result.stdout.strip()
        return version if version else "Unknown"
    except Exception:
        return "Unknown"


def _get_os_name() -> Optional[str]:
    try:
        with open(OS_RELEASE_PATH, "r") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
        return "Unknown"
    except Exception:
        return "Unknown"
    
    
def _get_hostname() -> str:
    try:
        return platform.node()
    except Exception:
        return "Unknown"


def _get_architecture() -> str:
    try:
        return platform.machine()
    except Exception:
        return "Unknown"


def _get_cpu_model() -> str:
    try:
        with open("/proc/cpuinfo", "r") as f:

            for line in f:

                if "Hardware" in line or "Model" in line:
                    return line.split(":", 1)[1].strip()

                if "model name" in line:
                    return line.split(":", 1)[1].strip()

        return "Unknown"

    except Exception:
        return "Unknown"


def _get_serial() -> str:
    paths = [
        "/sys/firmware/devicetree/base/serial-number",
        "/proc/device-tree/serial-number",
    ]

    for path in paths:

        try:
            with open(path, "r") as f:
                return f.read().strip("\x00\n")

        except Exception:
            pass

    return "Unknown"