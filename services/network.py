"""Network information service.

Migrated to remote execution: all of these commands (ip, hostname,
resolv.conf, ping, systemctl) describe the *NanoPC's* network, so they
must run on the Nano over SSH rather than on the laptop running Textual.
"""

import json

from services.remote import run_remote


# Bundled remote script: gathers everything network.py needs to display
# (primary IP, internet reachability, interfaces+status, gateway, DNS,
# data-usage-monitor status/service) in ONE SSH round trip instead of the
# 7+ separate calls the individual get_*() functions below would add up
# to if called one after another for a full refresh. Individual functions
# are kept as-is for callers that only need one piece of data.
_BUNDLE_REMOTE_SCRIPT = r"""
import json, subprocess

def run(cmd, timeout=5):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception:
        return ""

def systemctl(mode, unit):
    try:
        result = subprocess.run(["systemctl", mode, unit], capture_output=True, text=True, timeout=3)
        return result.stdout.strip()
    except Exception:
        return ""

IGNORE_IFACES = ("lo", "wg1")

# ---- interfaces + per-interface up/down state, from ONE "ip -o link" ----
link_states = {}
for line in run(["ip", "-o", "link"]).splitlines():
    parts = line.split()
    if len(parts) < 2:
        continue
    name = parts[1].rstrip(":").split("@")[0]
    flags = parts[2] if len(parts) > 2 else ""
    link_states[name] = "Connected" if "UP" in flags and "LOWER_UP" in flags else "Down"

# ---- route metrics per interface + gateway/active-interface, from ONE
# "ip route" call (default route and subnet routes usually agree on
# metric per interface, so whichever is seen first is fine) ----
route_output = run(["ip", "route"])

metrics = {}
gateway = "-"
active_interface = "-"
for line in route_output.splitlines():
    parts = line.split()
    if "dev" in parts and "metric" in parts:
        iface = parts[parts.index("dev") + 1]
        metric = parts[parts.index("metric") + 1]
        metrics[iface] = metric
    if line.startswith("default") and active_interface == "-":
        gateway = line
        if "dev" in parts:
            active_interface = parts[parts.index("dev") + 1]

interfaces = []
for line in run(["ip", "-o", "addr"]).splitlines():
    parts = line.split()
    if len(parts) < 4:
        continue
    name = parts[1]
    if name in IGNORE_IFACES:
        continue
    interfaces.append({
        "name": name,
        "status": link_states.get(name, "Down"),
        "ip": parts[3],
        "metric": metrics.get(name, "-"),
    })

# ---- DNS ----
dns = []
for line in run(["cat", "/etc/resolv.conf"]).splitlines():
    if line.startswith("nameserver"):
        dns.append(line.split()[1])

# ---- primary IP ----
ip_output = run(["hostname", "-I"])
primary_ip = ip_output.split()[0] if ip_output else "-"

# ---- internet reachability ----
try:
    ping_result = subprocess.run(
        ["ping", "-c", "1", "-W", "2", "8.8.8.8"], capture_output=True, timeout=5
    )
    internet_ok = ping_result.returncode == 0
except Exception:
    internet_ok = False

# ---- data usage monitor ----
active = systemctl("is-active", "data-usage-monitor.service")
enabled = systemctl("is-enabled", "data-usage-monitor.service")

data = {
    "ip_address": primary_ip,
    "internet": internet_ok,
    "interfaces": interfaces,
    "gateway": gateway,
    "route": gateway,
    "active_interface": active_interface,
    "dns": dns,
    "data_usage_monitor_active_raw": active,
    "data_usage_monitor_enabled_raw": enabled,
}

print(json.dumps(data))
"""


def _map_active(status):
    return {
        "active": "Enabled",
        "inactive": "Disabled",
        "failed": "Failed",
        "activating": "Starting",
        "deactivating": "Stopping",
    }.get(status, "Unknown")


def _map_enabled(status):
    return {
        "enabled": "Enabled",
        "disabled": "Disabled",
        "masked": "Masked",
        "not-found": "Not Found",
    }.get(status, "Unknown")


def get_network_bundle():
    """Everything the dashboard/network screens need, in one SSH call.

    Returns a dict combining what get_network_summary(), get_network_details(),
    get_data_usage_monitor_status(), and get_data_usage_monitor_service()
    would have returned together:

        ip_address, internet ("Connected"/"Disconnected"),
        interfaces, gateway, route, dns,
        data_usage_monitor_status, data_usage_monitor_service
    """

    result = run_remote(["python3", "-c", _BUNDLE_REMOTE_SCRIPT], timeout=10)

    if not result.ok:
        status = result.status_word()
        return {
            "ip_address": "-",
            "internet": "Disconnected",
            "interfaces": [],
            "gateway": "-",
            "route": "-",
            "active_interface": "-",
            "dns": [],
            "data_usage_monitor_status": status,
            "data_usage_monitor_service": status,
        }

    try:
        raw = json.loads(result.stdout)
    except Exception:
        return {
            "ip_address": "-",
            "internet": "Disconnected",
            "interfaces": [],
            "gateway": "-",
            "route": "-",
            "active_interface": "-",
            "dns": [],
            "data_usage_monitor_status": "Unknown",
            "data_usage_monitor_service": "Unknown",
        }

    return {
        "ip_address": raw.get("ip_address", "-"),
        "internet": "Connected" if raw.get("internet") else "Disconnected",
        "interfaces": raw.get("interfaces", []),
        "gateway": raw.get("gateway", "-"),
        "route": raw.get("route", "-"),
        "active_interface": raw.get("active_interface", "-"),
        "dns": raw.get("dns", []),
        "data_usage_monitor_status": _map_active(raw.get("data_usage_monitor_active_raw", "")),
        "data_usage_monitor_service": _map_enabled(raw.get("data_usage_monitor_enabled_raw", "")),
    }


def run_command(command):
    """Run a command on the Nano and return its stdout (empty string on
    failure) - kept as the same helper name/shape other functions in this
    module already used, just remote now instead of local.
    """
    result = run_remote(command, timeout=5)
    return result.stdout if result.ok else ""


def get_network_summary():

    internet = check_internet()

    return {
        "ip_address": get_primary_ip(),
        "internet": "Connected" if internet else "Disconnected",
    }


def get_network_details():

    return {
        "interfaces": get_interfaces(),
        "gateway": get_gateway(),
        "dns": get_dns(),
        "route": get_default_route(),
    }


def get_interfaces():

    interfaces = []

    output = run_command(["ip", "-o", "addr"])

    ignore = ["lo", "wg1"]

    for line in output.splitlines():

        parts = line.split()

        if len(parts) < 4:
            continue

        name = parts[1]

        if name in ignore:
            continue

        ip = parts[3]

        status = get_interface_status(name)

        interfaces.append({
            "name": name,
            "status": status,
            "ip": ip,
        })

    return interfaces


def get_interface_status(interface):

    output = run_command(["ip", "link", "show", interface])

    if "state UP" in output:
        return "Connected"

    return "Down"


def get_primary_ip():

    output = run_command(["hostname", "-I"])

    if output:
        return output.split()[0]

    return "-"


def get_gateway():

    output = run_command(["ip", "route"])

    for line in output.splitlines():

        if line.startswith("default"):

            return line

    return "-"


def get_default_route():

    return get_gateway()


def get_dns():

    dns = []

    output = run_command(["cat", "/etc/resolv.conf"])

    for line in output.splitlines():

        if line.startswith("nameserver"):

            dns.append(
                line.split()[1]
            )

    return dns


def check_internet():
    """Check whether the *Nano* has internet access (not the laptop)."""

    result = run_remote(["ping", "-c", "1", "-W", "2", "8.8.8.8"], timeout=5)
    return result.ok


def get_data_usage_monitor_status():

    result = run_remote(
        ["systemctl", "is-active", "data-usage-monitor.service"],
        timeout=3,
    )

    if not result.ok and result.error_kind in ("offline", "timeout", "auth", "not_found"):
        return "Unknown"

    status = result.stdout.strip()

    if status == "active":
        return "Enabled"
    elif status == "inactive":
        return "Disabled"
    elif status == "failed":
        return "Failed"
    elif status == "activating":
        return "Starting"
    elif status == "deactivating":
        return "Stopping"

    return "Unknown"


def get_data_usage_monitor_service():

    result = run_remote(
        ["systemctl", "is-enabled", "data-usage-monitor.service"],
        timeout=3,
    )

    if not result.ok and result.error_kind in ("offline", "timeout", "auth", "not_found"):
        return "Unknown"

    status = result.stdout.strip()

    if status == "enabled":
        return "Enabled"
    elif status == "disabled":
        return "Disabled"
    elif status == "masked":
        return "Masked"
    elif status == "not-found":
        return "Not Found"

    return "Unknown"
