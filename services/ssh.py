"""Nano sshd status/history service.

This reports on the *Nano's* SSH daemon (is it running, is it enabled,
recent login history) - a different concern from services/remote.py,
which is the transport WE use to reach the Nano in the first place.

Migrated to remote execution: systemctl/journalctl now run on the Nano
over SSH instead of on the laptop.
"""

import datetime

from services.remote import run_remote


def get_ssh_status():

    result = run_remote(["systemctl", "is-active", "ssh"], timeout=3)

    if not result.ok and result.error_kind in ("offline", "timeout", "auth", "not_found"):
        return result.status_word()

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


def get_ssh_service():

    result = run_remote(["systemctl", "is-enabled", "ssh"], timeout=3)

    if not result.ok and result.error_kind in ("offline", "timeout", "auth", "not_found"):
        return result.status_word()

    status = result.stdout.strip()

    if status == "enabled":
        return "Enabled"
    elif status == "disabled":
        return "Disabled"

    return "Unknown"


def get_ssh_history(limit=25):

    cmd = (
        "sudo journalctl -u ssh "
        "| grep -E 'Accepted password|Failed password|Invalid user|Disconnected from|Connection closed|PAM.*authentication failures' "
        "| tail -" + str(limit)
    )

    result = run_remote(cmd, timeout=8)

    if not result.ok and result.error_kind in ("offline", "timeout", "auth", "not_found"):
        return [
            {
                "date": "-",
                "time": "-",
                "event": "ERROR",
                "description": result.status_word(),
            }
        ]

    try:

        logs = []

        for line in result.stdout.splitlines():

            parts = line.split()

            if len(parts) < 6:
                continue

            # -------------------------
            # Date and time
            # -------------------------

            month = parts[0]
            day = parts[1]
            time_str = parts[2]

            try:

                year = datetime.datetime.now().year

                date = datetime.datetime.strptime(
                    f"{month} {day} {year}",
                    "%b %d %Y"
                ).strftime(
                    "%d %b %Y"
                )

            except Exception:

                date = f"{day} {month}"

            # -------------------------
            # Remove:
            # PC4-01-08-19
            # sshd[1234]:
            # -------------------------

            description = " ".join(parts[5:])

            # -------------------------
            # Determine event
            # -------------------------

            if "Accepted" in description:

                event = "LOGIN"

            elif "Failed" in description:

                event = "FAILED"

            elif "Disconnected" in description:

                event = "DISCONNECT"

            elif "session closed" in description:

                event = "CLOSED"

            elif "PAM" in description and "authentication failures" in description:
                event = "CRITICAL"

            else:
                event = "UNKNOWN"

            # -------------------------
            # Store
            # -------------------------

            logs.append(
                {
                    "date": date,
                    "time": time_str,
                    "event": event,
                    "description": description
                }
            )

        # newest first

        return logs[::-1]

    except Exception as e:

        return [
            {
                "date": "-",
                "time": "-",
                "event": "ERROR",
                "description": str(e)
            }
        ]
