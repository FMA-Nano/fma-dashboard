"""Network information service."""

import subprocess


def run_command(command):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
        )

        return result.stdout.strip()

    except Exception:
        return ""


        
        
        
def get_network_summary():

    interfaces = get_interfaces()

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

    output = run_command( ["ip", "-o", "addr"] )

    ignore = [ "lo", "wg1", ]

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

    output = run_command( [ "ip", "link", "show", interface ] )


    if "state UP" in output:
        return "Connected"

    return "Down"



def get_primary_ip():
    
    output = run_command( [ "hostname", "-I" ] )
    
    if output:
        return output.split()[0]

    return "-"



def get_gateway():

    output = run_command( [ "ip", "route" ] )

    for line in output.splitlines():

        if line.startswith("default"):

            return line

    return "-"



def get_default_route():

    return get_gateway()



def get_dns():

    dns = []

    output = run_command( [ "cat", "/etc/resolv.conf" ] )


    for line in output.splitlines():

        if line.startswith("nameserver"):

            dns.append(
                line.split()[1]
            )


    return dns



def check_internet():

    result = subprocess.run(
        [
            "ping",
            "-c",
            "1",
            "-W",
            "2",
            "8.8.8.8"
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def get_data_usage_monitor_status():
    try:
        result = subprocess.run(
            [
                "systemctl",
                "is-active",
                "data-usage-monitor.service",
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )

        status = result.stdout.strip()

        status = result.stdout.strip()

        if status == "active":
            return "Enabled"

        elif status == "inactive":
            return "Disabled"

        return "Unknown"
    
    except Exception:

        return "Unknown"
        
        
def get_data_usage_monitor_service():
    try:
        result = subprocess.run(
            [
                "systemctl",
                "is-enabled",
                "data-usage-monitor.service",
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )

        status = result.stdout.strip()

        if status == "enabled":
            return "Enabled"

        elif status == "disabled":
            return "Disabled"

        return "Unknown"

    except Exception:

        return "Unknown"