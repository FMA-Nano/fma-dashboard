from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static

from widgets.status_card import StatusCard

from services import system as system_service
from services import network as network_service
from services import coms as coms_service
from services.refresh import refresh_manager
from services import firewall as firewall_service
from services import wireguard as wireguard_service
from services import ssh as ssh_service
from services import wifi as wifi_service

class DashboardPage(VerticalScroll):
    """Landing page: system health, network, communications, services, recent events."""

    BINDINGS = [
        ("up", "cursor_up", "Scroll Up"),
        ("down", "cursor_down", "Scroll Down"),
    ]

    def compose(self):

        system = system_service.get_system_status()
        net = network_service.get_network_summary()
        coms = coms_service.get_devices()

        # ------------------------
        # ---- Devices Ports -----
        # ------------------------ 
        lcd = coms_service.get_device_status("DET")
        fc = coms_service.get_device_status("FC")
        atg = coms_service.get_atg_status()
        
        # ------------------------
        # ------ Fuctions --------
        # ------------------------ 
        firewall = firewall_service.get_firewall_status()
        wireguard = wireguard_service.get_wireguard_status()
        ssh = ssh_service.get_ssh_status()
        data_monitor = network_service.get_data_usage_monitor_status()
        
        # ------------------------
        # ------ Services --------
        # ------------------------ 
        firewall_ser = firewall_service.get_firewall_service()
        wireguard_ser = wireguard_service.get_wireguard_service() 
        ssh_ser = ssh_service.get_ssh_service()
        data_monitor_ser = network_service.get_data_usage_monitor_service()
        

        system = system_service.get_system_status()
        
        yield Static("[bold]Dashboard Test[/bold]", classes="page-title")
        
        self.info_card = StatusCard("Nano Information", [
            ("Hostname", system["hostname"]),
            ("Firmware", system["firmware"]),
        ])
        yield self.info_card
        

        with Horizontal(classes="card-row"):
            # System
            self.system_card = StatusCard("System Health", [
                ("CPU", system["cpu"]),
                ("RAM", system["ram"]),
                ("Storage", system["disk"]),
                ("Temperature", system["temperature"]),
                ("Up Time", system["uptime"]),
                ("Load", system["load"]),
            ])
            yield self.system_card

            # Network
            self.network_card = StatusCard("Network", [
                ("IP Address", net["ip_address"]),
                ("Internet", net["internet"]),
                ("WireGuard", wireguard),
                ("Firewall", firewall),
                ("SSH", ssh),
                ("Data Monitor", data_monitor),
            ])
            yield self.network_card

            # Coms
            self.coms_card = StatusCard("Communications", [
                ("LCD", lcd),
                ("Flow Controller", fc),
                ("ATG", atg),
                ("Total Devices", str(len(coms.devices))),
            ])
            yield self.coms_card

            # Services
            self.service_card = StatusCard("Services (On Boot Startup)", [
                ("WireGuard", wireguard_ser),
                ("Firewall", firewall_ser),
                ("SSH", ssh_ser),
                ("Data Monitor", data_monitor_ser),
            ])
            yield self.service_card


        with Horizontal(classes="card-row"):
            wifi = wifi_service.get_wifi_status()
            status = "Connected" if wifi["connected"] else "Disconnected"
            hotspot = wifi_service.get_hotspot_status()
                           
            self.wifi_card = StatusCard("WiFi Settings",[
                ("Module", "Enabled" if wifi["enabled"] else "Disabled"),
                ("Status", status),
                ("SSID", wifi["ssid"]),
                ])
            yield self.wifi_card
            
            self.hotspotcard = StatusCard("Hotspot Settings",[
                ("Status", hotspot["status"]),
                ("Name", hotspot["name"]),
                ])
            yield self.hotspotcard

        
    def on_mount(self) -> None:
        # Re-run refresh_data() every REFRESH_SECONDS while this page exists.
        self.set_interval(5, self.refresh_data)


    def refresh_data(self):
        
        # ------------------------
        # ---Refresh Cronjobs ----
        # ------------------------ 
        coms = coms_service.get_devices()
        lcd = coms_service.get_device_status("DET")
        fc = coms_service.get_device_status("FC")
        atg = coms_service.get_atg_status()
        
        self.coms_card.update_rows([
            ("LCD", lcd),
            ("Flow Controller", fc),
            ("ATG", atg),
            ("Total Devices", str(len(coms.devices))),
        ])

        # ------------------------
        # -- Refresh System ------
        # ------------------------ 
        system = system_service.get_system_status()
        
        self.system_card.update_rows([
            ("CPU", system["cpu"]),
            ("RAM", system["ram"]),
            ("Disk", system["disk"]),
            ("Temperature", system["temperature"]),
            ("Up Time", system["uptime"]),
            ("Load", system["load"]),
        ])

        # ------------------------
        # -- Refresh Fuctions ----
        # ------------------------ 
        net = network_service.get_network_summary()
        firewall = firewall_service.get_firewall_status()
        ssh = ssh_service.get_ssh_status()
        data_monitor = network_service.get_data_usage_monitor_status()
        wireguard = wireguard_service.get_wireguard_status()
        
        self.network_card.update_rows([
            ("IP Address", net["ip_address"]),
            ("Internet", net["internet"]),
            ("WireGuard", wireguard),
            ("Firewall", firewall),
            ("SSH", ssh),
            ("Data Monitor", data_monitor),
        ])

        # ------------------------
        # -- Refresh Services ----
        # ------------------------ 
        firewall_serv = firewall_service.get_firewall_service()
        ssh_serv = ssh_service.get_ssh_service()
        wireguard_serv = wireguard_service.get_wireguard_service()
        data_monitor_serv = network_service.get_data_usage_monitor_service()
        
        self.service_card.update_rows([
            ("WireGuard", wireguard_serv),
            ("Firewall", firewall_serv),
            ("SSH", ssh_serv),
            ("Data Monitor", data_monitor_serv),
        ])
        
        # ------------------------
        # ------- Wifi -----------
        # ------------------------ 
        wifi = wifi_service.get_wifi_status()
        status = "Connected" if wifi["connected"] else "Disconnected"
        hotspot = wifi_service.get_hotspot_status()
                        
        self.wifi_card.update_rows([
            ("Module", "Enabled" if wifi["enabled"] else "Disabled"),
            ("Status", status),
            ("SSID", wifi["ssid"]),
            ])

        
        self.hotspotcard.update_rows([
            ("Status", hotspot["status"]),
            ("Name", hotspot["name"]),
            ])