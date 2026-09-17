"""UPS (UPS6910C-24) status service.

The UPS monitoring script on the Nano writes its latest reading to a
single JSON file (not a rotating log), so this is a straightforward
remote file read + JSON parse - no bundling/multiple-command trickery
needed like the network/system services.
"""

import json
import time

from services.remote import run_remote
from services.config import get_nano

UPS_STATUS_PATH = "/home/pi/ST500V3/LogFiles/UPS/ups_status.json"


def _mv_to_v(value):
    try:
        return f"{float(value) / 1000:.2f} V"
    except (TypeError, ValueError):
        return "-"


def _ma_to_a(value):
    try:
        return f"{float(value) / 1000:.2f} A"
    except (TypeError, ValueError):
        return "-"


def _mw_to_w(value):
    try:
        return f"{float(value) / 1000:.2f} W"
    except (TypeError, ValueError):
        return "-"


def _format_age(timestamp):
    """How long ago the UPS status file was last written, e.g. "5s ago".
    Used to tell a genuinely fresh reading apart from a stale file left
    behind by a monitoring script that has since stopped running.
    """
    try:
        seconds = time.time() - float(timestamp)
    except (TypeError, ValueError):
        return "-"

    if seconds < 0:
        return "-"
    if seconds < 60:
        return f"{seconds:.0f}s ago"
    if seconds < 3600:
        return f"{seconds / 60:.0f}m ago"
    return f"{seconds / 3600:.1f}h ago"


def get_ups_monitor_status():
    """Whether ups_monitor.service is currently running (live status)."""

    result = run_remote(["systemctl", "is-active", "ups_monitor.service"], timeout=3)

    if not result.ok and result.error_kind in ("offline", "timeout", "auth", "not_found"):
        return result.status_word()

    status = result.stdout.strip()

    return {
        "active": "Enabled",
        "inactive": "Disabled",
        "failed": "Failed",
        "activating": "Starting",
        "deactivating": "Stopping",
    }.get(status, "Unknown")


def get_ups_monitor_service():
    """Whether ups_monitor.service is enabled to start at boot."""

    result = run_remote(["systemctl", "is-enabled", "ups_monitor.service"], timeout=3)

    if not result.ok and result.error_kind in ("offline", "timeout", "auth", "not_found"):
        return result.status_word()

    status = result.stdout.strip()

    return {
        "enabled": "Enabled",
        "disabled": "Disabled",
        "masked": "Masked",
        "not-found": "Not Found",
        "static": "Static",
    }.get(status, "Unknown")


def get_ups_status():
    """Read and interpret the UPS's latest status file.

    Returns a dict of display-ready fields, or a dict with every value
    set to a status word ("Offline"/"Timeout"/etc, or "Not Found" if the
    file doesn't exist yet) on failure, so the dashboard card always has
    something sensible to show rather than crashing on a KeyError.
    """

    result = run_remote(["cat", UPS_STATUS_PATH], timeout=5)

    fallback_keys = (
        "power_mode", "battery_pct", "battery_voltage", "battery_full",
        "charge_status", "converter_status", "temperature",
        "input_voltage", "output_voltage", "output_current", "output_power",
        "shutdown_countdown", "on_battery_since", "read_ok", "last_updated",
    )

    if not result.ok:
        status = result.status_word()
        return {key: status for key in fallback_keys}

    try:
        data = json.loads(result.stdout)
    except Exception:
        return {key: "Parse Error" for key in fallback_keys}

    power_mode = data.get("power_mode", "")

    return {
        "power_mode": power_mode.capitalize() if power_mode else "Unknown",
        "battery_pct": f"{data.get('battery_pct', '-')}%" if data.get("battery_pct") is not None else "-",
        "battery_voltage": _mv_to_v(data.get("battery_mv")),
        "battery_full": "Yes" if data.get("battery_full") else "No",
        "charge_status": str(data.get("charge_status", "-")).capitalize(),
        "converter_status": str(data.get("converter_status", "-")).capitalize(),
        "temperature": f"{data.get('temp_c', '-')}\u00b0C" if data.get("temp_c") is not None else "-",
        "input_voltage": _mv_to_v(data.get("uin_mv")),
        "output_voltage": _mv_to_v(data.get("uout_mv")),
        "output_current": _ma_to_a(data.get("uout_ma")),
        "output_power": _mw_to_w(data.get("uout_power_mw")),
        "shutdown_countdown": f"{data.get('shutdown_countdown_s', '-')}s" if data.get("shutdown_countdown_s") is not None else "-",
        "on_battery_since": data.get("on_battery_since") or "N/A",
        "read_ok": "Yes" if data.get("read_ok") else "No",
        "last_updated": _format_age(data.get("timestamp")),
    }
