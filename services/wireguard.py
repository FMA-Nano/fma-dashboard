"""WireGuard status service.

Migrated to remote execution: `wg`/`systemctl` describe the Nano's VPN
state, so this now runs on the Nano over SSH. Note `sudo` is embedded in
the remote command string (runs on the Nano), never as `sudo sshpass` on
the laptop.
"""

import time

from services.remote import run_remote


class WireGuardStatus:
    def __init__(self):
        self.interface_public_key = ""
        self.listen_port = 0
        self.peer_public_key = ""
        self.endpoint = ""
        self.allowed_ips = ""
        self.last_handshake = 0
        self.rx_bytes = 0
        self.tx_bytes = 0
        self.keepalive = ""
        self.enabled = False


def get_wireguard(interface="wg1"):
    # sudo calls can be slower than plain commands - give some headroom.
    result = run_remote(["sudo", "wg", "show", interface, "dump"], timeout=8)

    if not result.ok and not result.stdout:
        return None

    output = result.stdout
    lines = output.splitlines()

    if len(lines) < 2:
        return None

    interface_line = lines[0].split("\t")
    peer_line = lines[1].split("\t")

    status = WireGuardStatus()

    # Interface line: private_key, public_key, listen_port, fwmark
    status.interface_public_key = interface_line[1]
    status.listen_port = int(interface_line[2])

    # Peer line: public_key, preshared_key, endpoint, allowed_ips,
    #            latest_handshake, rx_bytes, tx_bytes, keepalive
    status.peer_public_key = peer_line[0]
    status.endpoint = peer_line[2]
    status.allowed_ips = peer_line[3]
    status.last_handshake = int(peer_line[4])
    status.rx_bytes = int(peer_line[5])
    status.tx_bytes = int(peer_line[6])
    status.keepalive = peer_line[7]

    status.enabled = get_wireguard_status(interface)

    return status


def get_wireguard_status(interface="wg1"):

    # Check if wg command exists on the Nano
    check = run_remote(["which", "wg"], timeout=5)

    if not check.ok:
        if check.error_kind in ("offline", "timeout", "auth", "not_found"):
            return check.status_word()
        return "Not Installed"

    # Check interface (sudo call - give a bit more headroom than plain commands)
    result = run_remote(["sudo", "wg", "show", interface], timeout=8)

    if not result.ok:
        if result.error_kind in ("offline", "timeout", "auth", "not_found"):
            return result.status_word()

        if "No such device" in result.stderr:
            return "Disabled"

        return "Unknown"

    return "Connected"


def format_bytes(value):
    mb = value / 1_000_000
    return f"{mb:.2f} MB"


def format_handshake(timestamp):
    if timestamp == 0:
        return "Never"

    seconds = int(time.time()) - timestamp

    if seconds < 60:
        return f"{seconds} seconds ago"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minutes ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hours ago"
    else:
        days = seconds // 86400
        return f"{days} days ago"


def get_wireguard_service(interface="wg1") -> str:
    result = run_remote(["systemctl", "is-enabled", f"wg-quick@{interface}"], timeout=3)

    if not result.ok and result.error_kind in ("offline", "timeout", "auth", "not_found"):
        return result.status_word()

    status = result.stdout.strip()

    if status == "enabled":
        return "Enabled"
    elif status == "disabled":
        return "Disabled"
    elif status == "not-found":
        return "Not Installed"
    else:
        return "Unknown"
