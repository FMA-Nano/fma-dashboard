from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static
from textual import work

from widgets.status_card import StatusCard

from services import system as system_service
from services import network as network_service
from services import coms as coms_service
from services import firewall as firewall_service
from services import wireguard as wireguard_service
from services import ssh as ssh_service
from services import wifi as wifi_service
from services import router as router_service
from services import ups as ups_service
from services import config as nano_config


def _interface_ip(interfaces, name):
    """Pull out the IPv4 address for a specific interface (e.g. "eth0",
    "wlan0") from the interfaces list returned by the network bundle.
    Returns "-" if that interface isn't present (not plugged in,
    disabled, or simply doesn't exist on this Nano).
    """
    for iface in interfaces:
        if iface.get("name") == name and "." in iface.get("ip", ""):
            # ip -o addr lists "1.2.3.4/24" - keep just the address part
            return iface["ip"].split("/")[0]
    return "-"


def _interface_ip_and_metric(interfaces, name):
    """Like _interface_ip(), but keeps the /CIDR suffix and appends the
    route metric, e.g. "192.168.1.48/24 metric 100" - useful for
    confirming at a glance which interface is actually preferred.
    Returns "-" if that interface isn't present.
    """
    for iface in interfaces:
        if iface.get("name") == name and "." in iface.get("ip", ""):
            metric = iface.get("metric", "-")
            return f"{iface['ip']} metric {metric}"
    return "-"


def _live_running_label(value):
    """Relabel a live status value for the "Programs (Is Running)" card.

    get_ssh_status()/the network bundle's data-usage-monitor status both
    return "Enabled"/"Disabled" (systemd's is-active mapped that way
    originally for boot-enabled checks elsewhere), but on a card
    specifically asking "is this running right now", "Active"/"Inactive"
    is the accurate wording - otherwise this card and the boot-enabled
    "Programs Services" card show the exact same words for two
    different questions, which is confusing. Anything else (Failed,
    Offline, Timeout, etc) passes through unchanged.
    """
    return {"Enabled": "Active", "Disabled": "Inactive"}.get(value, value)


class DashboardPage(VerticalScroll):
    """Landing page: system health, network, communications, services, recent events.

    Data is refreshed in three independent tiers, each on its own timer and
    each running its SSH calls in a background worker so the UI is never
    blocked waiting on the Nano:

        fast tier   (10s) - hardware status, communications, boot-enabled services
        network tier (20s) - network summary/interfaces + live status
        slow tier   (60s) - wifi settings, hotspot settings

    The Network card combines data from more than one tier (network info
    from the network tier AND wifi/hotspot from the slow tier), so its
    row list is built by _build_network_rows() using whatever the latest
    cached value from EACH tier is, called from every tier's apply
    method that touches it - this keeps the combined card consistent
    regardless of which tier's timer just fired.

    Programs (live status) and Programs Services (boot-enabled) are two
    separate cards, each with its own dedicated instance attribute so
    both stay independently refreshable.
    """

    FAST_INTERVAL = 10
    NETWORK_INTERVAL = 20
    SLOW_INTERVAL = 60

    BINDINGS = [
        ("up", "cursor_up", "Scroll Up"),
        ("down", "cursor_down", "Scroll Down"),
        ("up", "scroll_up", "Scroll Up"),
        ("down", "scroll_down", "Scroll Down"),
        ("pageup", "page_up", "Page Up"),
        ("pagedown", "page_down", "Page Down"),
    ]

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        # ---- System / hardware --
        self.system = {
            "hostname": "Loading...", "firmware": "Loading...",
            "cpu": "-", "ram": "-", "disk": "-",
            "temperature": "-", "uptime": "-", "load": "-",
        }

        # ---- Date / Time (timedatectl) --
        self.datetime_info = {
            "Local time": "Loading...", "Universal time": "-", "RTC time": "-",
            "Time zone": "-", "System clock synchronized": "-",
            "NTP service": "-", "RTC in local TZ": "-",
        }

        # ---- Communications ------
        self.lcd = "-"
        self.fc = "-"
        self.atg = "-"

        # ---- Network tier (live status) --------
        self.net = {"ip_address": "-", "internet": "-", "active_interface": "-", "interfaces": []}
        self.firewall = "-"
        self.wireguard = "-"
        self.ssh = "-"
        self.data_monitor = "-"

        # ---- Fast tier (boot-enabled status) -------
        self.firewall_ser = "-"
        self.wireguard_ser = "-"
        self.ssh_ser = "-"
        self.data_monitor_ser = "-"
        self.router_timer_ser = "-"
        self.ups_monitor_ser = "-"

        # ---- WiFi / hotspot tier -
        self.wifi = {"enabled": False, "connected": False, "ssid": "-", "signal": "-"}
        self.hotspot = {"status": "-", "name": "-"}

        # ---- Router / Modem (network tier) -
        self.router = {}
        self.apn = {}
        self.router_timer = "-"

        # ---- UPS (network tier) -
        self.ups = {}
        self.ups_monitor = "-"

        # ---- Cards ---------------
        self.info_card = None
        self.system_card = None
        self.datetime_card = None
        self.network_card = None
        self.coms_card = None
        self.service_card = None       # Programs (live status)
        self.service_boot_card = None  # Programs Services (On Boot Startup)
        self.router_card = None
        self.ups_card = None

    # ------------------------------------------------------------------
    # Row builder - Network combines data from two tiers (network tier
    # for internet/interfaces, slow tier for wifi/hotspot), so it's built
    # fresh from current state every time either tier refreshes.
    # ------------------------------------------------------------------

    def _build_datetime_rows(self):

        d = self.datetime_info

        return [
            ("Local Time", d.get("Local time", "-")),
            ("Universal Time", d.get("Universal time", "-")),
            ("RTC Time", d.get("RTC time", "-")),
            ("Time Zone", d.get("Time zone", "-")),
            ("Clock Synchronized", d.get("System clock synchronized", "-")),
            ("NTP Service", d.get("NTP service", "-")),
            ("RTC in Local TZ", d.get("RTC in local TZ", "-")),
        ]

    def _build_network_rows(self):

        interfaces = self.net.get("interfaces", [])

        return [
            ("Internet", self.net["internet"]),
            ("Active Interface", self.net.get("active_interface", "-")),
            ("Ethernet IP", _interface_ip_and_metric(interfaces, "eth0")),
            ("WiFi IP", _interface_ip_and_metric(interfaces, "wlan0")),

            ("", ""),
            ("[bold]WiFi[/bold]", ""),
            ("Module", "Enabled" if self.wifi["enabled"] else "Disabled"),
            ("Status", "Connected" if self.wifi["connected"] else "Disconnected"),
            ("SSID", self.wifi["ssid"]),
            ("Signal", self.wifi.get("signal", "-")),

            ("", ""),
            ("[bold]Hotspot[/bold]", ""),
            ("Status", self.hotspot["status"]),
            ("Name", self.hotspot["name"]),
        ]

    def _build_ups_rows(self):

        ups = self.ups

        return [
            ("Power Mode", ups.get("power_mode", "-")),
            ("Battery", ups.get("battery_pct", "-")),
            ("Battery Voltage", ups.get("battery_voltage", "-")),
            ("Battery Full", ups.get("battery_full", "-")),
            ("Charge Status", ups.get("charge_status", "-")),
            ("Converter", ups.get("converter_status", "-")),
            ("Temperature", ups.get("temperature", "-")),
            ("Input Voltage", ups.get("input_voltage", "-")),
            ("Output Voltage", ups.get("output_voltage", "-")),
            ("Output Current", ups.get("output_current", "-")),
            ("Output Power", ups.get("output_power", "-")),
            ("Shutdown Countdown", ups.get("shutdown_countdown", "-")),
            ("On Battery Since", ups.get("on_battery_since", "-")),
            ("Read OK", ups.get("read_ok", "-")),
            ("Last Updated", ups.get("last_updated", "-")),
        ]

    def _build_router_rows(self):
        """Combines app.db-sourced router status (SIM/Modem/Operator/etc,
        network tier) with the live-fetched APN (slow tier) - built fresh
        from current state on every call so either tier's refresh can
        call this and always produce a complete, consistent row set.
        """

        rows = [
            ("SIM", self.router.get("SIM", "")),
            ("SIM CCID", self.router.get("SIM CCID", "")),
            ("Modem", self.router.get("Modem", "")),
            ("Operator", self.router.get("Operator", "")),
            ("Network", self.router.get("Network", "")),
            ("Signal (CSQ)", self.router.get("CSQ", "")),
            ("RSRP", self.router.get("RSRP", "")),
            ("RSRQ", self.router.get("RSRQ", "")),
            ("SINR", self.router.get("SINR", "")),
            ("APN", self.apn.get("apn", "")),
        ]

        if self.apn.get("dualsim") not in ("", "0", None):
            rows.append(("APN (SIM 2)", self.apn.get("apn2", "")))

        rows += [
            ("IP Address", self.router.get("IP", "")),
            ("Gateway", self.router.get("Gateway", "")),
            ("DNS", self.router.get("DNS", "")),
            ("Connection", self.router.get("Connection", "")),
            ("Uptime", self.router.get("Uptime", "")),
        ]

        return rows

    def compose(self):

        conn = nano_config.get_nano()

        # -----------------------------
        # System Information
        # -----------------------------

        yield Static("[bold]System Information[/bold]", classes="page-title")

        with Horizontal(classes="card-row"):

            self.info_card = StatusCard("Nano Information", [
                ("Hostname", self.system["hostname"]),
                ("Firmware", self.system["firmware"]),
                ("Login Host", conn["host"]),
                ("Login Port", str(conn.get("port", 22))),
                ("Login User", conn["user"]),
            ])
            yield self.info_card

            self.system_card = StatusCard("System Health", [
                ("CPU", self.system["cpu"]),
                ("RAM", self.system["ram"]),
                ("Storage", self.system["disk"]),
                ("Temperature", self.system["temperature"]),
                ("Up Time", self.system["uptime"]),
                ("Load", self.system["load"]),
            ])
            yield self.system_card

            self.datetime_card = StatusCard("Date Time Info", self._build_datetime_rows())
            yield self.datetime_card

        # -----------------------------
        # Communications
        # -----------------------------

        yield Static("[bold]Coms / Programs [/bold]", classes="page-title")

        with Horizontal(classes="card-row"):

            self.coms_card = StatusCard("Communications", [
                ("LCD", self.lcd),
                ("Flow Controller", self.fc),
                ("ATG", self.atg),
            ])
            yield self.coms_card

            self.service_card = StatusCard("Programs (Is Running)", [
                ("WireGuard", self.wireguard),
                ("Firewall", self.firewall),
                ("SSH", _live_running_label(self.ssh)),
                ("Data Monitor", _live_running_label(self.data_monitor)),
                ("Router Modem Timer", self.router_timer),
                ("UPS Monitor", _live_running_label(self.ups_monitor)),
            ])
            yield self.service_card

            self.service_boot_card = StatusCard("Programs Services (On Boot Startup)", [
                ("WireGuard", self.wireguard_ser),
                ("Firewall", self.firewall_ser),
                ("SSH", self.ssh_ser),
                ("Data Monitor", self.data_monitor_ser),
                ("Router Modem Timer", self.router_timer_ser),
                ("UPS Monitor", self.ups_monitor_ser),
            ])
            yield self.service_boot_card

        # -----------------------------
        # Network / Router
        # -----------------------------

        yield Static("[bold]Network[/bold]", classes="page-title")

        with Horizontal(classes="card-row"):

            self.network_card = StatusCard("Network", self._build_network_rows())
            yield self.network_card

            self.router_card = StatusCard("Router / Modem", self._build_router_rows())
            yield self.router_card

            self.ups_card = StatusCard("UPS (UPS6910C-24)", self._build_ups_rows())
            yield self.ups_card

    def on_mount(self) -> None:

        # Kick off one of each tier immediately so the page fills in as
        # soon as possible after mount, then let the intervals take over.
        self.refresh_fast_tier()
        self.refresh_network_tier()
        self.refresh_slow_tier()

        self.set_interval(self.FAST_INTERVAL, self.refresh_fast_tier)
        self.set_interval(self.NETWORK_INTERVAL, self.refresh_network_tier)
        self.set_interval(self.SLOW_INTERVAL, self.refresh_slow_tier)

    def force_refresh(self) -> None:
        """Immediately re-fetch every tier, bypassing the visibility
        check - used when the active Nano connection changes, so no
        stale data from a previous Nano lingers on this page.
        """
        self._fetch_fast_tier()
        self._fetch_network_tier()
        self._fetch_slow_tier()

    # ------------------------------------------------------------------
    # Fast tier (10s): hardware status, communications, boot-enabled services
    # ------------------------------------------------------------------

    def refresh_fast_tier(self):
        if not self.display:
            return
        self._fetch_fast_tier()

    @work(thread=True, exclusive=True, group="dashboard-fast")
    def _fetch_fast_tier(self):

        system = system_service.get_system_status()
        datetime_info = system_service.get_datetime_info()

        coms = coms_service.get_devices()
        lcd = coms_service.get_device_status(coms.devices, "DET")
        fc = coms_service.get_device_status(coms.devices, "FC")
        atg = coms_service.get_atg_status()

        firewall_ser = firewall_service.get_firewall_service()
        wireguard_ser = wireguard_service.get_wireguard_service()
        ssh_ser = ssh_service.get_ssh_service()
        data_monitor_ser = network_service.get_data_usage_monitor_service()
        router_timer_ser = router_service.get_router_modem_timer_service()
        ups_monitor_ser = ups_service.get_ups_monitor_service()

        self.app.call_from_thread(
            self._apply_fast_tier,
            system, datetime_info, lcd, fc, atg,
            firewall_ser, wireguard_ser, ssh_ser, data_monitor_ser,
            router_timer_ser, ups_monitor_ser,
        )

    def _apply_fast_tier(self, system, datetime_info, lcd, fc, atg,
                          firewall_ser, wireguard_ser, ssh_ser, data_monitor_ser,
                          router_timer_ser, ups_monitor_ser):

        self.system = system
        self.datetime_info = datetime_info
        self.lcd, self.fc, self.atg = lcd, fc, atg
        self.firewall_ser = firewall_ser
        self.wireguard_ser = wireguard_ser
        self.ssh_ser = ssh_ser
        self.data_monitor_ser = data_monitor_ser
        self.router_timer_ser = router_timer_ser
        self.ups_monitor_ser = ups_monitor_ser

        if self.info_card:
            conn = nano_config.get_nano()
            self.info_card.update_rows([
                ("Hostname", system["hostname"]),
                ("Firmware", system["firmware"]),
                ("Login Host", conn["host"]),
                ("Login Port", str(conn.get("port", 22))),
                ("Login User", conn["user"]),
            ])

        if self.system_card:
            self.system_card.update_rows([
                ("CPU", system["cpu"]),
                ("RAM", system["ram"]),
                ("Storage", system["disk"]),
                ("Temperature", system["temperature"]),
                ("Up Time", system["uptime"]),
                ("Load", system["load"]),
            ])

        if self.datetime_card:
            self.datetime_card.update_rows(self._build_datetime_rows())

        if self.coms_card:
            self.coms_card.update_rows([
                ("LCD", lcd),
                ("Flow Controller", fc),
                ("ATG", atg),
            ])

        if self.service_boot_card:
            self.service_boot_card.update_rows([
                ("WireGuard", wireguard_ser),
                ("Firewall", firewall_ser),
                ("SSH", ssh_ser),
                ("Data Monitor", data_monitor_ser),
                ("Router Modem Timer", router_timer_ser),
                ("UPS Monitor", ups_monitor_ser),
            ])

    # ------------------------------------------------------------------
    # Network tier (20s): network summary + live wg/firewall/ssh status
    # ------------------------------------------------------------------

    def refresh_network_tier(self):
        if not self.display:
            return
        self._fetch_network_tier()

    @work(thread=True, exclusive=True, group="dashboard-network")
    def _fetch_network_tier(self):

        net = network_service.get_network_bundle()

        firewall = firewall_service.get_firewall_status()
        wireguard = wireguard_service.get_wireguard_status()
        ssh_status = ssh_service.get_ssh_status()
        router = router_service.get_router_modem_status()
        router_timer = router_service.get_router_modem_timer_status()
        ups = ups_service.get_ups_status()
        ups_monitor = ups_service.get_ups_monitor_status()

        self.app.call_from_thread(
            self._apply_network_tier, net, firewall, wireguard, ssh_status, router,
            router_timer, ups, ups_monitor,
        )

    def _apply_network_tier(self, net, firewall, wireguard, ssh_status, router,
                             router_timer, ups, ups_monitor):

        self.net = net
        self.firewall = firewall
        self.wireguard = wireguard
        self.ssh = ssh_status
        self.data_monitor = net.get("data_usage_monitor_status", "-")
        self.router = router or {}
        self.router_timer = router_timer
        self.ups = ups or {}
        self.ups_monitor = ups_monitor

        if self.network_card:
            self.network_card.update_rows(self._build_network_rows())

        if self.ups_card:
            self.ups_card.update_rows(self._build_ups_rows())

        if self.service_card:
            self.service_card.update_rows([
                ("WireGuard", wireguard),
                ("Firewall", firewall),
                ("SSH", _live_running_label(ssh_status)),
                ("Data Monitor", _live_running_label(self.data_monitor)),
                ("Router Modem Timer", router_timer),
                ("UPS Monitor", _live_running_label(ups_monitor)),
            ])

        if self.router_card:
            self.router_card.update_rows(self._build_router_rows())

    # ------------------------------------------------------------------
    # Slow tier (60s): wifi settings, hotspot settings
    # ------------------------------------------------------------------

    def refresh_slow_tier(self):
        if not self.display:
            return
        self._fetch_slow_tier()

    @work(thread=True, exclusive=True, group="dashboard-slow")
    def _fetch_slow_tier(self):

        bundle = wifi_service.get_wifi_bundle()
        apn = router_service.get_router_apn()

        self.app.call_from_thread(self._apply_slow_tier, bundle["wifi"], bundle["hotspot"], apn)

    def _apply_slow_tier(self, wifi, hotspot, apn):

        self.wifi = wifi
        self.hotspot = hotspot
        self.apn = apn or {}

        if self.network_card:
            self.network_card.update_rows(self._build_network_rows())

        if self.router_card:
            self.router_card.update_rows(self._build_router_rows())
