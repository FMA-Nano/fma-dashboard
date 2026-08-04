import subprocess


def run_command(cmd):

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3
        )

        return result.stdout.strip()

    except Exception:
        return ""


def is_wifi_enabled(interface="wlan0"):

    output = run_command(
        [
            "ip",
            "link",
            "show",
            interface
        ]
    )

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


    output = run_command(
        [
            "iw",
            "dev",
            interface,
            "link"
        ]
    )


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
        [
            "nmcli",
            "-t",
            "-f",
            "NAME,TYPE",
            "connection",
            "show",
            "--active"
        ]
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