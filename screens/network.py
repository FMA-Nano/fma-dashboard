from textual.containers import VerticalScroll
from textual.widgets import Static
from widgets.status_card import StatusCard
from services import network as network_service
from services import wireguard as wireguard_service
from services import wifi as wifi_service

REFRESH_SECONDS = 5


class NetworkPage(VerticalScroll):
    
    BINDINGS = [
        ("up", "cursor_up", "Scroll Up"),
        ("down", "cursor_down", "Scroll Down"),
    ]
        
    def compose(self):
        data = network_service.get_network_details()
        wifi = wifi_service.get_wifi_status()

        status = "Connected" if wifi["connected"] else "Disconnected"
        hotspot = wifi_service.get_hotspot_status()
    
        yield Static("[bold]Network[/bold]", classes="page-title")
              
                
        yield Static("[bold]WiFi[/bold]", classes="section-title")
        self.wifi_card = StatusCard("WiFi Settings",[
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
        yield self.wifi_card
        
                
        yield Static("[bold]Interfaces[/bold]", classes="section-title")
        yield Static(self._render_interfaces(data), id="interfaces", classes="info-block")

        
        self.wifi_card = StatusCard("Routing / DNS",[
            ("Gateway", data['gateway']),
            ("DNS", ', '.join(data['dns'])),
            ("Route", data['route']),
            ])
        yield self.wifi_card
        
        
        yield Static("[bold]WireGuard[/bold]", classes="section-title")
        yield Static(self._render_wireguard(), id="wireguard", classes="info-block")


    def on_mount(self) -> None:
        # Re-run refresh_data() every REFRESH_SECONDS while this page exists.
        self.set_interval(REFRESH_SECONDS, self.refresh_data)

    def refresh_data(self) -> None:
        # Skip work if this page isn't the one currently on screen -
        # ContentSwitcher hides inactive pages via `display`, so there's no
        # point re-running subprocess calls (sudo wg show, etc.) for a page
        # nobody is looking at.
        if not self.display:
            return

        self.wifi_card = StatusCard("WiFi Settings",[
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
        yield self.wifi_card
        
        
        self.wifi_card = StatusCard("Routing / DNS",[
            ("Gateway", data['gateway']),
            ("DNS", ', '.join(data['dns'])),
            ("Route", data['route']),
            ])
        yield self.wifi_card
        
        
        hotspot = wifi_service.get_hotspot_status()
    
    
        data = network_service.get_network_details()
        # self.query_one("#wifi", Static).update(self._render_wifi(wifi))
        self.query_one("#interfaces", Static).update(self._render_interfaces(data))
        # self.query_one("#routing", Static).update(self._render_routing(data))
        self.query_one("#wireguard", Static).update(self._render_wireguard())



    def _render_interfaces(self, data: dict) -> str:
        return "\n".join(
            f"{iface['name']:<8} {iface['status']:<12} {iface['ip']}"
            for iface in data["interfaces"]
        )



    def _render_wireguard(self) -> str:
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
