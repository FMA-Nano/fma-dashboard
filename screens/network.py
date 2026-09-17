from textual.containers import VerticalScroll
from textual.widgets import Static
from textual import work

from widgets.status_card import StatusCard
from services import network as network_service
from services import wireguard as wireguard_service
from services import wifi as wifi_service

# How often each part of this page is refreshed. WiFi/hotspot config
# barely ever changes, so it doesn't need to be checked as often as the
# network interfaces/WireGuard tunnel.
WIFI_REFRESH_SECONDS = 60
NETWORK_REFRESH_SECONDS = 20

LOADING = "Loading..."


class NetworkPage(VerticalScroll):
    """compose() only builds placeholder widgets - the actual SSH fetches
    happen in background workers (both tiers), so this screen never
    blocks the UI thread on mount.
    """

    BINDINGS = [
        ("up", "cursor_up", "Scroll Up"),
        ("down", "cursor_down", "Scroll Down"),
        ("up", "scroll_up", "Scroll Up"),
        ("down", "scroll_down", "Scroll Down"),
        ("pageup", "page_up", "Page Up"),
        ("pagedown", "page_down", "Page Down"),
    ]

    def compose(self):

        yield Static("[bold]WiFi[/bold]", classes="page-title")
        self.wifi_card = StatusCard("WiFi Settings", [
            ("[bold]WiFi[/bold]", ""),
            ("Module", LOADING),
            ("Status", LOADING),
            ("SSID", LOADING),
            ("Signal", LOADING),
            ("Frequency", LOADING),
            ("Bitrate", LOADING),
            ("", ""),
            ("[bold]WiFi Hotspot[/bold]", ""),
            ("Status", LOADING),
            ("Name", LOADING),
        ])
        yield self.wifi_card

        yield Static("[bold]Interfaces[/bold]", classes="page-title")
        yield Static(LOADING, id="interfaces", classes="info-block")

        self.routing_card = StatusCard("Routing / DNS", [
            ("Gateway", LOADING),
            ("DNS", LOADING),
            ("Route", LOADING),
        ])
        yield self.routing_card

        yield Static("[bold]WireGuard[/bold]", classes="page-title")
        yield Static(LOADING, id="wireguard", classes="info-block")

    def on_mount(self) -> None:
        self.refresh_wifi_tier()
        self.refresh_network_tier()
        self.set_interval(WIFI_REFRESH_SECONDS, self.refresh_wifi_tier)
        self.set_interval(NETWORK_REFRESH_SECONDS, self.refresh_network_tier)

    def on_show(self) -> None:
        # Refresh right away when the user switches to this page.
        self._fetch_wifi_tier()
        self._fetch_network_tier()

    def force_refresh(self) -> None:
        """Immediately re-fetch both tiers, bypassing the visibility
        check - used when the active Nano connection changes.
        """
        self._fetch_wifi_tier()
        self._fetch_network_tier()

    # ------------------------------------------------------------------
    # WiFi / hotspot tier (60s)
    # ------------------------------------------------------------------

    def refresh_wifi_tier(self) -> None:
        if not self.display:
            return
        self._fetch_wifi_tier()

    @work(thread=True, exclusive=True, group="network-page-wifi")
    def _fetch_wifi_tier(self) -> None:
        bundle = wifi_service.get_wifi_bundle()
        self.app.call_from_thread(self._apply_wifi_tier, bundle["wifi"], bundle["hotspot"])

    def _apply_wifi_tier(self, wifi, hotspot) -> None:
        status = "Connected" if wifi["connected"] else "Disconnected"

        self.wifi_card.update_rows([
            ("[bold]WiFi[/bold]", ""),
            ("Module", "Enabled" if wifi["enabled"] else "Disabled"),
            ("Status", status),
            ("SSID", wifi["ssid"]),
            ("Signal", wifi["signal"]),
            ("Frequency", wifi["frequency"]),
            ("Bitrate", wifi["bitrate"]),
            ("", ""),
            ("[bold]WiFi Hotspot[/bold]", ""),
            ("Status", hotspot["status"]),
            ("Name", hotspot["name"]),
        ])

    # ------------------------------------------------------------------
    # Network / routing / WireGuard tier (20s)
    # ------------------------------------------------------------------

    def refresh_network_tier(self) -> None:
        if not self.display:
            return
        self._fetch_network_tier()

    @work(thread=True, exclusive=True, group="network-page-network")
    def _fetch_network_tier(self) -> None:
        net = network_service.get_network_bundle()
        wg = wireguard_service.get_wireguard("wg1")
        self.app.call_from_thread(self._apply_network_tier, net, wg)

    def _apply_network_tier(self, net, wg) -> None:
        self.routing_card.update_rows([
            ("Gateway", net["gateway"]),
            ("DNS", ", ".join(net["dns"])),
            ("Route", net["route"]),
        ])

        self.query_one("#interfaces", Static).update(self._render_interfaces(net))
        self.query_one("#wireguard", Static).update(self._render_wireguard(wg))

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render_interfaces(self, data: dict) -> str:
        return "\n".join(
            f"{iface['name']:<8} {iface['status']:<12} {iface['ip']:<20} metric {iface.get('metric', '-')}"
            for iface in data["interfaces"]
        )

    def _render_wireguard(self, wg=None) -> str:
        if wg is None:
            wg = wireguard_service.get_wireguard("wg1")

        if wg is None:
            return "[red]Unable to read WireGuard status.[/red]"

        rx = wireguard_service.format_bytes(wg.rx_bytes)
        tx = wireguard_service.format_bytes(wg.tx_bytes)
        handshake = wireguard_service.format_handshake(wg.last_handshake)
        enabled_text = "[green]Enabled[/green]" if wg.enabled else "[red]Disabled[/red]"

        return (
            "Interface       wg1\n"
            f"Public Key      {wg.interface_public_key}\n"
            f"Listen Port     {wg.listen_port}\n"
            f"Status          {enabled_text}\n"
            "\n"
            f"Peer            {wg.peer_public_key}\n"
            f"Endpoint        {wg.endpoint}\n"
            f"Allowed IPs     {wg.allowed_ips}\n"
            f"Handshake       {handshake}\n"
            f"Traffic         RX {rx}  TX {tx}"
        )
