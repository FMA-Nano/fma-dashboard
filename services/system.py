"""System status service.

Migrated to remote execution: this used to read /proc, /sys, /etc directly
on the machine running Textual. Now the Textual dashboard runs on the
laptop, so all of this information describes the *NanoPC* and must be
collected from it over SSH.

To avoid one SSH round-trip per value (hostname, cpu, ram, disk, temp,
uptime, load, kernel, os, arch, cpu model, serial, firmware) this module
sends a single small Python script to the Nano that gathers everything in
one connection and prints it back as JSON, which is then parsed here.

The Nano itself still only needs its standard library + sqlite3 (both
built in to Python) - no extra packages need to be installed there.

Public interface is unchanged: get_system_status() still returns the same
dict of string values the screens already expect.
"""

import json
from typing import Dict

from services.remote import run_remote, query_remote_sqlite, execute_remote_sqlite
from services.config import APP_DB_PATH

UNKNOWN = "Unknown"

# This script runs *on the Nano*. It intentionally avoids any third-party
# packages (no psutil) so it works on whatever plain Python 3 is already
# on the Nano's SD card.
_REMOTE_SCRIPT = r"""
import json, os, platform, subprocess, time

def cpu_percent():
    def read():
        with open("/proc/stat") as f:
            parts = f.readline().split()
        return [int(x) for x in parts[1:8]]
    try:
        first = read()
        time.sleep(0.1)
        second = read()
        idle_delta = second[3] - first[3]
        total_delta = sum(second) - sum(first)
        if total_delta <= 0:
            return "Unknown"
        return "%.0f%%" % (100.0 * (1.0 - (idle_delta / total_delta)))
    except Exception:
        return "Unknown"

def ram_percent():
    try:
        values = {}
        with open("/proc/meminfo") as f:
            for line in f:
                key, _, rest = line.partition(":")
                values[key.strip()] = int(rest.strip().split()[0])
        total = values.get("MemTotal")
        available = values.get("MemAvailable")
        if not total or available is None:
            return "Unknown"
        return "%.0f%%" % (100.0 * (1 - (available / total)))
    except Exception:
        return "Unknown"

def disk_percent():
    try:
        usage = os.statvfs("/")
        total = usage.f_blocks * usage.f_frsize
        free = usage.f_bfree * usage.f_frsize
        if total == 0:
            return "Unknown"
        return "%.0f%%" % (100.0 * (1 - (free / total)))
    except Exception:
        return "Unknown"

def temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            raw = int(f.read().strip())
        return "%.1f\u00b0C" % (raw / 1000.0)
    except Exception:
        return "Unknown"

def uptime():
    try:
        with open("/proc/uptime") as f:
            seconds = float(f.read().split()[0])
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        if days >= 1:
            return "%d days" % days
        if hours >= 1:
            return "%d hours" % hours
        return "%d minutes" % minutes
    except Exception:
        return "Unknown"

def load_average():
    try:
        with open("/proc/loadavg") as f:
            parts = f.read().split()
        return "%s, %s, %s" % (parts[0], parts[1], parts[2])
    except Exception:
        return "Unknown"

def kernel_version():
    try:
        result = subprocess.run(["uname", "-r"], capture_output=True, text=True, timeout=3)
        version = result.stdout.strip()
        return version if version else "Unknown"
    except Exception:
        return "Unknown"

def os_name():
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
        return "Unknown"
    except Exception:
        return "Unknown"

def cpu_model():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "Hardware" in line or "Model" in line:
                    return line.split(":", 1)[1].strip()
                if "model name" in line:
                    return line.split(":", 1)[1].strip()
        return "Unknown"
    except Exception:
        return "Unknown"

def serial():
    for path in ("/sys/firmware/devicetree/base/serial-number", "/proc/device-tree/serial-number"):
        try:
            with open(path) as f:
                return f.read().strip("\x00\n")
        except Exception:
            pass
    return "Unknown"

def firmware():
    try:
        import sqlite3
        conn = sqlite3.connect(__DB_PATH__)
        cur = conn.cursor()
        cur.execute("SELECT TypeString FROM config WHERE id = 3")
        row = cur.fetchone()
        conn.close()
        if row is None:
            return "No Row Found"
        return row[0]
    except Exception as e:
        return "ERROR: %s" % e

data = {
    "hostname": platform.node() or "Unknown",
    "firmware": firmware(),
    "cpu": cpu_percent(),
    "ram": ram_percent(),
    "disk": disk_percent(),
    "temperature": temperature(),
    "uptime": uptime(),
    "load": load_average(),
    "kernel": kernel_version(),
    "os": os_name(),
    "architecture": platform.machine() or "Unknown",
    "cpu_model": cpu_model(),
    "serial": serial(),
}

print(json.dumps(data))
""".replace("__DB_PATH__", repr(APP_DB_PATH))


def get_system_status() -> Dict[str, str]:
    """Return system status for the NanoPC, fetched over SSH.

    On any remote failure (offline/timeout/etc) every field falls back to
    "Unknown"/the connection status so screens don't need special-case
    handling - they already treat these fields as opaque display strings.
    """

    result = run_remote(["python3", "-c", _REMOTE_SCRIPT], timeout=10)

    if not result.ok:
        status = result.status_word()
        return {
            "hostname": status,
            "firmware": status,
            "cpu": UNKNOWN,
            "ram": UNKNOWN,
            "disk": UNKNOWN,
            "temperature": UNKNOWN,
            "uptime": UNKNOWN,
            "load": UNKNOWN,
            "kernel": UNKNOWN,
            "os": UNKNOWN,
            "architecture": UNKNOWN,
            "cpu_model": UNKNOWN,
            "serial": UNKNOWN,
        }

    try:
        return json.loads(result.stdout)
    except Exception:
        status = "Parse Error"
        return {key: status for key in (
            "hostname", "firmware", "cpu", "ram", "disk", "temperature",
            "uptime", "load", "kernel", "os", "architecture",
            "cpu_model", "serial",
        )}


def get_datetime_info() -> Dict[str, str]:
    """Parsed output of `timedatectl` - local/UTC/RTC time, timezone, and
    whether the clock is NTP-synchronized. Returns a dict keyed exactly
    as timedatectl labels each line (Local time, Universal time, RTC
    time, Time zone, System clock synchronized, NTP service, RTC in
    local TZ), or a dict of status words on failure so callers don't
    need special-case handling.
    """

    fields = [
        "Local time", "Universal time", "RTC time", "Time zone",
        "System clock synchronized", "NTP service", "RTC in local TZ",
    ]

    result = run_remote(["timedatectl"], timeout=5)

    if not result.ok:
        status = result.status_word()
        return {field: status for field in fields}

    data = {}

    for line in result.stdout.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key in fields:
            data[key] = value

    for field in fields:
        data.setdefault(field, "-")

    return data


def sync_rtc_from_system_clock():
    """Write the current system clock time into the hardware RTC
    (equivalent to `sudo hwclock --systohc`). Useful when the RTC has
    drifted or was never set - this only copies whatever the system
    clock currently reads into the RTC, it doesn't fix a wrong system
    clock itself (that's what NTP/timedatectl handles separately).

    Returns (success: bool, output: str).
    """

    result = run_remote(["sudo", "-n", "hwclock", "--systohc"], timeout=10)

    output_parts = []
    if result.stdout:
        output_parts.append(result.stdout)
    if result.stderr:
        output_parts.append(result.stderr)
    output = "\n".join(output_parts)

    if not result.ok:
        return False, output or result.status_word()

    return True, output or "RTC synced with system clock."


def get_controller_state():
    """Read the current ApplicationId/TypeId pair for ControllerState
    from app.db. This pair controls whether the Nano's LCD shows its
    normal operational screens or a special admin menu:
        99 / 99  -> admin menu enabled
        1  / 0   -> normal operation

    Returns {"application_id": ..., "type_id": ...}, or None on failure
    (offline, row not found, etc).
    """

    rows = query_remote_sqlite(
        APP_DB_PATH,
        "SELECT ApplicationId, TypeId FROM Config WHERE FieldName = 'ControllerState' LIMIT 1",
    )

    if not rows:
        return None

    application_id, type_id = rows[0]
    return {"application_id": application_id, "type_id": type_id}


def set_controller_state(application_id, type_id):
    """Write new ApplicationId/TypeId values for ControllerState.
    Returns True on success. A reboot is required afterward for this to
    actually take effect on the LCD - call reboot_nano() separately once
    this succeeds.
    """

    return execute_remote_sqlite(
        APP_DB_PATH,
        "UPDATE Config SET ApplicationId = ?, TypeId = ? WHERE FieldName = 'ControllerState'",
        params=[application_id, type_id],
    )


def reboot_nano():
    """Reboot the Nano itself - the same device the dashboard is SSH'd
    into, so the connection is expected to drop as part of this rather
    than cleanly returning a success response (run_remote() itself
    never raises - a dropped connection here just comes back as an
    ordinary failed RemoteResult, which is fine to ignore). The
    dashboard's own connectivity watchdog will notice the Nano come
    back up and reconnect/refresh everything automatically, the same
    way it already handles any other temporary loss of connection.
    """

    run_remote(["sudo", "-n", "reboot"], timeout=5)


def restart_software():
    """Run the ST500V3 controller's own restart script - mirrors option
    3 ("Software has been restarted successfully") from the Nano's
    on-device admin menu. Runs from /home/pi/ since the script is
    invoked with a relative path (./bin/restart.sh) in the original
    menu system.

    Returns (success: bool, output: str).
    """

    result = run_remote("cd /home/pi/ && ./bin/restart.sh", timeout=30)

    output_parts = []
    if result.stdout:
        output_parts.append(result.stdout)
    if result.stderr:
        output_parts.append(result.stderr)
    output = "\n".join(output_parts)

    if not result.ok:
        return False, output or result.status_word()

    return True, output or "Software has been restarted successfully."


def stop_all_software():
    """Kill every running python process on the Nano - mirrors option 2
    ("Controller stop all Python processes") from the Nano's on-device
    admin menu. This is deliberately blunt (matches the original menu
    command exactly) and will stop the main controller software along
    with anything else currently running under python - use
    restart_software() afterward to bring it back if it doesn't restart
    on its own.

    Returns (success: bool, output: str).
    """

    result = run_remote(["sudo", "-n", "killall", "python"], timeout=10)

    output_parts = []
    if result.stdout:
        output_parts.append(result.stdout)
    if result.stderr:
        output_parts.append(result.stderr)
    output = "\n".join(output_parts)

    if not result.ok:
        return False, output or result.status_word()

    return True, output or "Controller stop all Python processes."
