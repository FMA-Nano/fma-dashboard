"""The exact router_settings.py content, deployed onto the Nano before
each use rather than reimplemented here. This script's payload-building
logic (40+ fields, connect-mode branching, checkbox quirks matching a
real captured browser submission) is specific, fragile, router-firmware-
dependent behavior that was already built and tested against the real
hardware - reusing it verbatim avoids the risk of a subtly wrong
reimplementation misconfiguring the router.
"""

ROUTER_SETTINGS_SCRIPT = r'''#!/usr/bin/env python3

import re
import sys
import subprocess


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

ROUTER_IP = "192.168.1.1"
USERNAME = "admin"
PASSWORD = "admin"

HTTP_ID = "TID7f5d98b97159b7d1"


# ---------------------------------------------------------
# Parse JavaScript object (same logic as router_status.py)
# ---------------------------------------------------------

def parse_js_object(text, var_name):

    match = re.search(
        rf"{var_name}\s*=\s*\{{(.*?)\}};",
        text,
        re.DOTALL
    )

    if not match:
        return {}

    body = match.group(1)

    pairs = re.findall(
        r"""['"]([\w\.]+)['"]\s*:\s*['"]([^'"]*)['"]""",
        body
    )

    return dict(pairs)


# ---------------------------------------------------------
# Get current cellular settings (basic-cellular.asp)
# ---------------------------------------------------------

def get_cellular_settings():

    url = (
        f"http://{ROUTER_IP}/basic-cellular.asp"
        f"?_http_id={HTTP_ID}"
    )

    try:

        result = subprocess.run(
            [
                "curl",
                "-s",
                "--connect-timeout", "5",
                "--max-time", "10",
                "-u", f"{USERNAME}:{PASSWORD}",
                url
            ],
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.returncode != 0:
            print("ERROR: Could not retrieve cellular settings page")
            return None

        if not result.stdout.strip():
            print("ERROR: Router returned empty data")
            return None

        return parse_js_object(result.stdout, "nvram")

    except Exception as e:

        print(f"ERROR: {e}")

        return None


# ---------------------------------------------------------
# Change the APN
# ---------------------------------------------------------

def set_apn(new_apn, sim=1):
    """
    Change the cellular APN on the router.

    sim=1 -> updates CelldialApn  (SIM 1)
    sim=2 -> updates CelldialApn2 (SIM 2)
    """

    nvram = get_cellular_settings()

    if not nvram:
        print("ERROR: Could not read current settings, aborting APN change")
        return False

    suffix = "" if sim == 1 else "2"
    apn_field = f"CelldialApn{suffix}"

    # -------------------------------------------------
    # Work out connect-mode dependent hidden fields
    # (mirrors the router's own save() JavaScript)
    # -------------------------------------------------

    ppp_demand = nvram.get("ppp_demand", "0")

    if ppp_demand in ("0", "1"):
        # Keep Alive / Connect On Demand
        cellConMode = "1"
        TimeControl = "0"
        RingControl = "0"

    elif ppp_demand == "2":
        # Connect On Schedule
        cellConMode = "0"
        TimeControl = "1"
        RingControl = "0"

    elif ppp_demand == "3":
        # SMS & Ring
        cellConMode = "0"
        TimeControl = "0"
        RingControl = "1" if nvram.get("RingControl") == "1" else "0"

    else:
        # Manual
        cellConMode = "0"
        TimeControl = "0"
        RingControl = "0"

    # NOTE: the router's own save() JS sets SmControl = 1
    # unconditionally, regardless of connect mode (confirmed
    # from a captured real browser submission). Replicating
    # that quirk here rather than "fixing" it, since matching
    # real router behavior is what avoids the CGI crashing.
    SmControl = "1"

    sim_flag = "2" if nvram.get("dualsim") == "2" else "1"

    # -------------------------------------------------
    # Build the full payload, matching a real captured
    # browser submission field-for-field. We resend the
    # router's existing values for every field, and only
    # change the APN field itself. This firmware's CGI
    # crashes (empty reply) if expected fields are missing,
    # so completeness matters more than minimalism here.
    # -------------------------------------------------

    payload = {
        "_nextpage": "/#basic-cellular.asp",
        "_nextwait": "5",
        "_service": "modem_checkdial-restart",
        "_reboot": "1",

        "cellConMode": cellConMode,
        "ims_enable": nvram.get("ims_enable", "0"),
        "PingEnable": nvram.get("PingEnable", "0"),
        "rx_tx_enable": nvram.get("rx_tx_enable", "0"),
        "sim_flag": sim_flag,
        "SSTimeEnable": nvram.get("SSTimeEnable", "0"),
        "RingControl": RingControl,
        "SmControl": SmControl,
        "TimeControl": TimeControl,
        "reset_modem": "0",
        "enable_modem": nvram.get("enable_modem", "1"),
        "band_lock_enable": nvram.get("band_lock_enable", "0"),
        "icmp_rtt_enable": nvram.get("icmp_rtt_enable", "0"),
        "lte_use_ppp": nvram.get("lte_use_ppp", "0"),

        "UtmsPingAddr": nvram.get("UtmsPingAddr", "8.8.8.8"),
        "UtmsPingAddr1": nvram.get("UtmsPingAddr1", "8.8.4.4"),
        "PingInterval": nvram.get("PingInterval", "60"),
        "PingMax": nvram.get("PingMax", "3"),
        "icmp_rtt_time": nvram.get("icmp_rtt_time", "50"),
        "icmp_action": nvram.get("icmp_action", "1"),
        "rx_tx_mode": nvram.get("rx_tx_mode", "0"),
        "rx_tx_check_int": nvram.get("rx_tx_check_int", "10"),
        "rx_tx_action": nvram.get("rx_tx_action", "0"),
        "ppp_custom": nvram.get("ppp_custom", ""),
        "ppp_demand": ppp_demand,
        "timeUpLink": nvram.get("timeUpLink", ""),
        "timeDownLink": nvram.get("timeDownLink", ""),
        "SSTimeUpLink": nvram.get("SSTimeUpLink", ""),
        "SSTimeDownLink": nvram.get("SSTimeDownLink", ""),
        "SmNum": nvram.get("SmNum", ""),
        "ppp_idletime": nvram.get("ppp_idletime", "5"),
        "ppp_redialperiod": nvram.get("ppp_redialperiod", "10"),
        "modem_mtu": nvram.get("modem_mtu", "0"),
        "tcp_server": nvram.get("tcp_server", ""),
        "tcp_port": nvram.get("tcp_port", ""),
        "smspasswd": nvram.get("smspasswd", ""),
        "cops_oper": nvram.get("cops_oper", ""),
        "dualsim": nvram.get("dualsim", "0"),
        "main_timeout": nvram.get("main_timeout", "10"),
        "backup_timeout": nvram.get("backup_timeout", "10"),

        "tdd_mode": nvram.get("tdd_mode", "only-lte"),
        "cellType": nvram.get("cellType", "0"),
        "cell_mode": nvram.get("cell_mode", "0"),
        "NR_type": nvram.get("NR_type", "0"),
        "cops_network": nvram.get("cops_network", "1"),
        "band_lock_num_sa": nvram.get("band_lock_num_sa", ""),
        "band_lock_num_nsa": nvram.get("band_lock_num_nsa", ""),
        "band_lock_num_lte": nvram.get("band_lock_num_lte", ""),

        "CelldialPincode": nvram.get(f"CelldialPincode{suffix}", ""),
        apn_field: new_apn,
        "CelldialUser": nvram.get(f"CelldialUser{suffix}", ""),
        "CelldialPwd": nvram.get(f"CelldialPwd{suffix}", ""),
        "CelldialNum": nvram.get(f"CelldialNum{suffix}", "*99#"),
        "auth_type": nvram.get(f"auth_type{suffix}", "0"),
        "local_ip": nvram.get(f"local_ip{suffix}", ""),

        "_http_id": HTTP_ID,
    }

    # -------------------------------------------------
    # Checked checkboxes are submitted as their own
    # "f_<name>=on" field alongside the hidden numeric
    # field. Only include the ones that are actually on.
    # -------------------------------------------------

    checkbox_pairs = [
        ("f_enable_modem", "enable_modem"),
        ("f_ims_enable", "ims_enable"),
        ("f_lte_use_ppp", "lte_use_ppp"),
        ("f_PingEnable", "PingEnable"),
        ("f_icmp_rtt_enable", "icmp_rtt_enable"),
        ("f_rx_tx_enable", "rx_tx_enable"),
        ("f_SSTimeEnable", "SSTimeEnable"),
        ("f_RingControl", "RingControl"),
        ("f_SmControl", "SmControl"),
        ("f_band_lock_enable", "band_lock_enable"),
    ]

    for checkbox_name, hidden_name in checkbox_pairs:
        if payload.get(hidden_name) == "1":
            payload[checkbox_name] = "on"

    url = f"http://{ROUTER_IP}/tomato.cgi"

    data_args = []

    for key, value in payload.items():
        data_args += ["--data-urlencode", f"{key}={value}"]

    try:

        result = subprocess.run(
            [
                "curl",
                "-v",
                "--connect-timeout", "5",
                "--max-time", "15",
                "-u", f"{USERNAME}:{PASSWORD}",
                "-X", "POST",
                "-H", f"Referer: http://{ROUTER_IP}/",
                "-H", f"Origin: http://{ROUTER_IP}",
                url,
                *data_args
            ],
            capture_output=True,
            text=True,
            timeout=20
        )

        if result.returncode != 0:
            print(f"ERROR: APN change request failed (curl exit code {result.returncode})")
            print("----- curl stderr/verbose -----")
            print(result.stderr)
            print("----- curl stdout -----")
            print(result.stdout)
            print("--------------------------------")
            return False

        print(f"APN change submitted: {apn_field} = {new_apn}")
        print("Router response (first 300 chars):")
        print(result.stdout[:300])

        return True

    except Exception as e:

        print(f"ERROR: {e}")

        return False


# ---------------------------------------------------------
# Reboot the router
#
# Some settings (like the APN) are written to the router's
# config immediately, but only take effect after a reboot.
# The GUI shows a banner saying so; this replicates clicking
# the router's own "Reboot" action.
# ---------------------------------------------------------

def reboot_router():

    payload = {
        "_reboot_now": "1",
        "_commit": "0",
        "_nvset": "0",
        "_http_id": HTTP_ID,
    }

    url = f"http://{ROUTER_IP}/tomato.cgi"

    data_args = []

    for key, value in payload.items():
        data_args += ["--data-urlencode", f"{key}={value}"]

    try:

        result = subprocess.run(
            [
                "curl",
                "-s",
                "--connect-timeout", "5",
                "--max-time", "15",
                "-u", f"{USERNAME}:{PASSWORD}",
                "-X", "POST",
                "-H", f"Referer: http://{ROUTER_IP}/",
                "-H", f"Origin: http://{ROUTER_IP}",
                url,
                *data_args
            ],
            capture_output=True,
            text=True,
            timeout=20
        )

        # A reboot often drops the connection mid-response,
        # or the router simply stops answering right after
        # accepting the request. Both are expected here, so
        # we don't treat curl's exit code as a hard failure.
        if result.returncode != 0:
            print(
                f"NOTE: curl exit code {result.returncode} "
                f"(expected if the router dropped the connection "
                f"to begin rebooting)"
            )
        else:
            print("Reboot request accepted by router.")

        print("Router should be back online in roughly 30-90 seconds.")

        return True

    except Exception as e:

        print(f"ERROR: {e}")

        return False


# ---------------------------------------------------------
# Command-line usage:
#   python3 router_settings.py <new_apn> [sim_number] [--reboot]
#   python3 router_settings.py --reboot-only
# ---------------------------------------------------------

def main():

    if len(sys.argv) < 2:
        print("Usage: python3 router_settings.py <new_apn> [sim_number] [--reboot]")
        print("       python3 router_settings.py --reboot-only")
        print("Example: python3 router_settings.py internet 1 --reboot")
        return 1

    if sys.argv[1] == "--reboot-only":
        success = reboot_router()
        return 0 if success else 1

    new_apn = sys.argv[1]

    do_reboot = "--reboot" in sys.argv

    remaining = [a for a in sys.argv[2:] if a != "--reboot"]
    sim = int(remaining[0]) if remaining else 1

    success = set_apn(new_apn, sim)

    if not success:
        return 1

    if do_reboot:
        print("Rebooting router to apply the new APN...")
        reboot_router()
    else:
        print(
            "APN saved. The router may need a reboot to fully apply it "
            "(run again with --reboot, or use --reboot-only)."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
