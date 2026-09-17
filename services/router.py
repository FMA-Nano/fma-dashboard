"""Router / modem status service.

Migrated to remote execution: app.db lives on the Nano, so it's now
queried over SSH instead of opened directly with sqlite3 locally. The
interpretation logic (Connected/Disconnected, N/A fill-in, etc) stays on
the laptop - only the raw row fetch is remote.
"""

import json

from services.router_settings_script import ROUTER_SETTINGS_SCRIPT

REMOTE_ROUTER_SETTINGS_PATH = "/tmp/router_settings.py"

# The router's admin page (192.168.1.1) is only reachable from the Nano's
# LAN side, not from the laptop - so reading the live APN has to run as a
# remote command, same as everything else here. This mirrors
# router_settings.py's own get_cellular_settings() (curl the router's
# basic-cellular.asp page, pull values out of its embedded "nvram = {...}"
# JS object) but executed on the Nano via a bundled remote script rather
# than locally, and only extracts the two APN fields (SIM 1 / SIM 2)
# rather than the whole settings page.
_APN_REMOTE_SCRIPT = r"""
import subprocess, re, json

ROUTER_IP = "192.168.1.1"
HTTP_ID = "TID7f5d98b97159b7d1"

try:
    result = subprocess.run(
        ["curl", "-s", "--connect-timeout", "5", "--max-time", "10",
         "-u", "admin:admin",
         f"http://{ROUTER_IP}/basic-cellular.asp?_http_id={HTTP_ID}"],
        capture_output=True, text=True, timeout=15,
    )
    text = result.stdout
except Exception:
    text = ""

def field(name):
    # Require the field name to be immediately followed by a quote, so
    # "CelldialApn" doesn't accidentally match inside "CelldialApn2".
    m = re.search(name + r"['\"]\s*:\s*['\"]([^'\"]*)", text)
    return m.group(1) if m else ""

print(json.dumps({
    "apn": field("CelldialApn"),
    "apn2": field("CelldialApn2"),
    "dualsim": field("dualsim") or "0",
}))
"""

from services.remote import query_remote_sqlite, run_remote
from services.config import APP_DB_PATH

APP_DB = APP_DB_PATH


def get_router_modem_status():

    try:
        rows = query_remote_sqlite(
            APP_DB,
            """
            SELECT TypeString
            FROM Config
            WHERE id = 68
              AND FieldName = 'RouterModemStatus'
            LIMIT 1
            """,
        )

        if rows is None:
            print("Router status error: could not reach Nano/query app.db")
            return {}

        if not rows or not rows[0] or not rows[0][0]:
            return {}

        data = json.loads(rows[0][0])

        # -----------------------------------------
        # Modem status
        # -----------------------------------------

        modem = data.get("Modem")

        if modem == "1":
            data["Modem"] = "Connected"
        else:
            data["Modem"] = "Disconnected"

            # If modem is disconnected,
            # all modem-related information is unavailable.
            for key in data:
                if key != "Modem":
                    data[key] = "N/A"

            return data

        # -----------------------------------------
        # SIM status
        # -----------------------------------------

        if data.get("SIM") == "1":
            data["SIM"] = "Inserted"
        else:
            data["SIM"] = "Not Inserted"

        # -----------------------------------------
        # SIM Flag
        # -----------------------------------------

        if data.get("SIM Flag") == "1":
            data["SIM Flag"] = "Ready"
        else:
            data["SIM Flag"] = "Not Ready"

        # -----------------------------------------
        # Connection
        # -----------------------------------------

        if data.get("Connection") == "1":
            data["Connection"] = "Connected"
        else:
            data["Connection"] = "Disconnected"

        # -----------------------------------------
        # Network
        # -----------------------------------------

        if not data.get("Network"):
            data["Network"] = "Not Connected"

        # -----------------------------------------
        # Empty values
        # -----------------------------------------

        for key in data:
            if data[key] == "":
                data[key] = "N/A"

        return data

    except Exception as e:
        print(f"Router status error: {e}")
        return {}


def get_router_apn():
    """Current cellular APN(s) configured on the router - read live from
    the router's own admin page each call (not stored in app.db, unlike
    the rest of the router status), since the APN can be changed at any
    time via the router's own interface, not just through this dashboard.

    Returns {"apn": ..., "apn2": ..., "dualsim": "0"/"1"} - apn2 is only
    meaningful when dualsim is "1"/"2" (a second SIM slot is in use).
    """

    result = run_remote(["python3", "-c", _APN_REMOTE_SCRIPT], timeout=12)

    if not result.ok:
        status = result.status_word()
        return {"apn": status, "apn2": status, "dualsim": "0"}

    try:
        return json.loads(result.stdout)
    except Exception:
        return {"apn": "Parse Error", "apn2": "Parse Error", "dualsim": "0"}


def get_router_modem_program_status():
    """Whether router-modem-status.service is currently running.

    This unit is timer-triggered and typically a oneshot - it runs
    briefly to pull fresh data into app.db, then returns to "inactive"
    once done. Seeing "Not Running" between runs is expected, not
    necessarily a fault - check get_router_modem_timer_status() for
    whether it's actually being scheduled to run at all.
    """

    result = run_remote(["systemctl", "is-active", "router-modem-status.service"], timeout=3)

    if not result.ok and result.error_kind in ("offline", "timeout", "auth", "not_found"):
        return result.status_word()

    status = result.stdout.strip()

    return {
        "active": "Running",
        "inactive": "Not Running",
        "failed": "Failed",
        "activating": "Starting",
        "deactivating": "Stopping",
    }.get(status, "Unknown")


def get_router_modem_program_service():
    """Whether router-modem-status.service is enabled at boot.

    Note: `systemctl is-enabled` can also return "static" for a unit
    with no [Install] section that's only ever started as a dependency
    of something else - exactly the case here, since it's triggered by
    router-modem-status.timer rather than being enabled directly. That's
    a normal, healthy state for a timer-triggered oneshot service, not
    an error - shown as "Static" rather than falling through to
    "Unknown" (which would look like a fault).
    """

    result = run_remote(["systemctl", "is-enabled", "router-modem-status.service"], timeout=3)

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


def get_router_modem_timer_status():
    """Whether router-modem-status.timer is active - i.e. whether the
    periodic pull is actually scheduled to run, regardless of whether
    the service itself happens to be mid-run at this exact moment.
    """

    result = run_remote(["systemctl", "is-active", "router-modem-status.timer"], timeout=3)

    if not result.ok and result.error_kind in ("offline", "timeout", "auth", "not_found"):
        return result.status_word()

    status = result.stdout.strip()

    return {
        "active": "Active",
        "inactive": "Inactive",
        "failed": "Failed",
    }.get(status, "Unknown")


def get_router_modem_timer_service():
    """Whether router-modem-status.timer is enabled to start at boot.

    This - not the service's own is-enabled state - is what actually
    answers "will this survive a reboot?" for a timer-triggered oneshot
    service. The service itself is typically "static" (no [Install]
    section, only ever started by the timer), so its is-enabled state
    can never tell you whether the whole mechanism comes back after a
    restart - only the timer's boot-enabled state can.
    """

    result = run_remote(["systemctl", "is-enabled", "router-modem-status.timer"], timeout=3)

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


# ---------------------------------------------------------------------------
# Router settings (APN change / reboot) - deploys the known-good
# router_settings.py onto the Nano before each use, so we always run our
# own current copy rather than depending on it having been manually
# placed there beforehand.
# ---------------------------------------------------------------------------

def _deploy_router_settings_script():
    """(Re)write router_settings.py onto the Nano via a heredoc. Cheap
    enough to do before every use - one extra SSH round trip - and
    guarantees the script on disk always matches this exact version.
    """
    heredoc = (
        f"cat > {REMOTE_ROUTER_SETTINGS_PATH} << 'ROUTERSETTINGSPY_EOF'\n"
        + ROUTER_SETTINGS_SCRIPT +
        "\nROUTERSETTINGSPY_EOF"
    )
    return run_remote(heredoc, timeout=10)


def _run_router_settings(args, timeout=30):
    """Deploy the script, then run it with the given CLI args. Returns
    (success, output) - output combines stdout+stderr so the caller can
    show the person exactly what the script printed either way.
    """

    deploy_result = _deploy_router_settings_script()

    if not deploy_result.ok:
        return False, f"Could not deploy router_settings.py to the Nano: {deploy_result.status_word()}"

    result = run_remote(["python3", REMOTE_ROUTER_SETTINGS_PATH] + list(args), timeout=timeout)

    output_parts = []
    if result.stdout:
        output_parts.append(result.stdout)
    if result.stderr:
        output_parts.append(result.stderr)
    output = "\n".join(output_parts)

    if not result.ok:
        return False, output or result.status_word()

    return True, output


def set_router_apn(new_apn, sim=1, reboot=False):
    """Change the router's cellular APN by running router_settings.py on
    the Nano (only the Nano can reach the router's LAN IP). Set
    reboot=True to also reboot the router immediately afterward so the
    change actually takes effect, rather than just being saved.

    Returns (success: bool, output: str) - output is whatever the script
    printed, for showing the person what actually happened.
    """

    args = [str(new_apn), str(sim)]

    if reboot:
        args.append("--reboot")

    return _run_router_settings(args, timeout=45 if reboot else 30)


def reboot_router():
    """Reboot the router only, without changing anything else - runs
    router_settings.py --reboot-only on the Nano.

    Returns (success: bool, output: str).
    """

    return _run_router_settings(["--reboot-only"], timeout=30)
