"""Firewall (UFW) status service.

Migrated to remote execution: ufw/systemctl describe the Nano's firewall,
so they now run on the Nano over SSH (sudo runs on the Nano, not via
`sudo sshpass` on the laptop).
"""

from services.remote import run_remote


def get_firewall_status():
    """
    Check whether the UFW firewall is currently active on the Nano.

    Returns:
        Enabled
        Disabled
        Not Installed
        Unknown
        Offline / Timeout / Auth Error (connection-level failures)
    """

    # sudo calls can be slower than plain commands (e.g. hostname
    # resolution during sudo's own logging step) - give this a bit more
    # room than the systemctl-only calls below.
    result = run_remote(["sudo", "-n", "ufw", "status"], timeout=6)

    if not result.ok and result.error_kind in ("offline", "timeout", "auth", "not_found"):
        return result.status_word()

    output = result.stdout.strip()

    if "Status: active" in output:
        return "Enabled"

    elif "Status: inactive" in output:
        return "Disabled"

    elif result.returncode not in (0, None):
        return "Not Installed"

    return "Unknown"


def get_firewall_service():
    """
    Check whether UFW is enabled at boot on the Nano.

    Returns:
        Enabled
        Disabled
        Not Installed
        Unknown
        Offline / Timeout / Auth Error (connection-level failures)
    """

    result = run_remote(["systemctl", "is-enabled", "ufw"], timeout=3)

    if not result.ok and result.error_kind in ("offline", "timeout", "auth", "not_found"):
        return result.status_word()

    status = result.stdout.strip()

    if status == "enabled":
        return "Enabled"

    elif status == "disabled":
        return "Disabled"

    elif status == "not-found":
        return "Not Installed"

    return "Unknown"
