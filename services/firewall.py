import subprocess


def get_firewall_status():
    """
    Check whether the UFW firewall is currently active.

    Returns:
        Enabled
        Disabled
        Not Installed
        Unknown
    """

    try:

        result = subprocess.run(
            ["sudo", "-n", "ufw", "status"],
            capture_output=True,
            text=True,
            timeout=3,
        )

        output = result.stdout.strip()

        if "Status: active" in output:
            return "Enabled"

        elif "Status: inactive" in output:
            return "Disabled"

        elif result.returncode != 0:
            return "Not Installed"

        return "Unknown"

    except subprocess.TimeoutExpired:
        return "Unknown"

    except FileNotFoundError:
        return "Not Installed"

    except Exception:
        return "Unknown"
    

def get_firewall_service():
    """
    Check whether UFW is enabled at boot.

    Returns:
        Enabled
        Disabled
        Not Installed
        Unknown
    """

    try:

        result = subprocess.run(
            ["systemctl", "is-enabled", "ufw"],
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

        return "Unknown"

    except subprocess.TimeoutExpired:
        return "Unknown"

    except FileNotFoundError:
        return "Not Installed"

    except Exception:
        return "Unknown"