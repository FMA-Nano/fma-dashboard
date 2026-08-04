import subprocess
import time


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
    result = subprocess.run(
        ["sudo", "wg", "show", interface, "dump"],
        capture_output=True,
        text=True,
    )

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


import subprocess


def get_wireguard_status(interface="wg1"):

    # Check if wg command exists
    check = subprocess.run(
        ["which", "wg"],
        capture_output=True,
        text=True
    )

    if check.returncode != 0:
        return "Not Installed"


    # Check interface
    result = subprocess.run(
        ["sudo", "wg", "show", interface],
        capture_output=True,
        text=True
    )


    if result.returncode != 0:

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
    try:
        result = subprocess.run(
            ["systemctl", "is-enabled", f"wg-quick@{interface}"],
            capture_output=True,
            text=True,
            timeout=3,
        )

        status = result.stdout.strip()

        if status == "enabled":
            return "Enabled"
        elif status == "disabled":
            return "Disabled"
        elif status == "not-found":
            return "Not Installed"
        else:
            return "Unknown"

    except FileNotFoundError:
        return "Not Installed"

    except Exception:
        return "Unknown"