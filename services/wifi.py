"""WiFi / hotspot status service.

Migrated to remote execution: ip/iw/nmcli describe the Nano's wireless
interfaces, so they now run on the Nano over SSH.
"""

import json

from services.remote import run_remote


# Bundled remote script: wifi status + hotspot status in ONE SSH round
# trip instead of 3 separate calls (ip link show, iw dev link, nmcli).
_BUNDLE_REMOTE_SCRIPT = r"""
import json, subprocess

def run(cmd, timeout=5):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception:
        return ""

interface = "%(interface)s"

link_output = run(["ip", "link", "show", interface])
wifi_enabled = "UP" in link_output

wifi = {
    "enabled": wifi_enabled,
    "connected": False,
    "status": "Disabled",
    "ssid": "-",
    "signal": "-",
    "frequency": "-",
    "bitrate": "-",
}

if wifi_enabled:
    iw_output = run(["iw", "dev", interface, "link"])

    if "Not connected." in iw_output:
        wifi["status"] = "Disconnected"
    else:
        wifi["connected"] = True
        wifi["status"] = "Connected"

        for line in iw_output.splitlines():
            line = line.strip()
            if line.startswith("SSID:"):
                wifi["ssid"] = line.replace("SSID:", "").strip()
            elif line.startswith("freq:"):
                wifi["frequency"] = line.replace("freq:", "").strip()
            elif line.startswith("signal:"):
                wifi["signal"] = line.replace("signal:", "").strip()
            elif line.startswith("tx bitrate:"):
                wifi["bitrate"] = line.replace("tx bitrate:", "").strip()

nmcli_output = run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"])

hotspot = {"enabled": False, "name": "-", "status": "Disabled"}

for line in nmcli_output.splitlines():
    if ":802-11-wireless" in line:
        hotspot["enabled"] = True
        hotspot["name"] = line.split(":")[0]
        hotspot["status"] = "Enabled"
        break

print(json.dumps({"wifi": wifi, "hotspot": hotspot}))
"""


def get_wifi_bundle(interface="wlan0"):
    """Wifi status + hotspot status in one SSH round trip.

    Returns {"wifi": <same shape as get_wifi_status()>, "hotspot": <same
    shape as get_hotspot_status()>}.
    """

    script = _BUNDLE_REMOTE_SCRIPT % {"interface": interface}
    result = run_remote(["python3", "-c", script], timeout=8)

    fallback_wifi = {
        "enabled": False, "connected": False, "status": "Unknown",
        "ssid": "-", "signal": "-", "frequency": "-", "bitrate": "-",
    }
    fallback_hotspot = {"enabled": False, "name": "-", "status": "Unknown"}

    if not result.ok:
        status = result.status_word()
        return {
            "wifi": {**fallback_wifi, "status": status},
            "hotspot": {**fallback_hotspot, "status": status},
        }

    try:
        data = json.loads(result.stdout)
        return {
            "wifi": data.get("wifi", fallback_wifi),
            "hotspot": data.get("hotspot", fallback_hotspot),
        }
    except Exception:
        return {"wifi": fallback_wifi, "hotspot": fallback_hotspot}


def run_command(cmd):
    result = run_remote(cmd, timeout=3)
    return result.stdout if result.ok else ""


def is_wifi_enabled(interface="wlan0"):

    output = run_command(["ip", "link", "show", interface])

    return "UP" in output


def get_wifi_status(interface="wlan0"):

    if not is_wifi_enabled(interface):

        return {
            "enabled": False,
            "connected": False,
            "status": "Disabled",
            "ssid": "-",
            "signal": "-",
            "frequency": "-",
            "bitrate": "-"
        }

    output = run_command(["iw", "dev", interface, "link"])

    if "Not connected." in output:

        return {
            "enabled": True,
            "connected": False,
            "status": "Disconnected",
            "ssid": "-",
            "signal": "-",
            "frequency": "-",
            "bitrate": "-"
        }

    data = {
        "enabled": True,
        "connected": True,
        "status": "Connected",
        "ssid": "-",
        "signal": "-",
        "frequency": "-",
        "bitrate": "-"
    }

    for line in output.splitlines():

        line = line.strip()

        if line.startswith("SSID:"):
            data["ssid"] = line.replace("SSID:", "").strip()

        elif line.startswith("freq:"):
            data["frequency"] = line.replace("freq:", "").strip()

        elif line.startswith("signal:"):
            data["signal"] = line.replace("signal:", "").strip()

        elif line.startswith("tx bitrate:"):
            data["bitrate"] = line.replace("tx bitrate:", "").strip()

    return data


def get_hotspot_status():

    output = run_command(
        ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"]
    )

    hotspot = {
        "enabled": False,
        "name": "-",
        "status": "Disabled",
    }

    for line in output.splitlines():

        if ":802-11-wireless" in line:

            hotspot["enabled"] = True
            hotspot["name"] = line.split(":")[0]
            hotspot["status"] = "Enabled"
            break

    return hotspot
