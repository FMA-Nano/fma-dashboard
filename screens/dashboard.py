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

import time


def write_speed_log(message):

    with open("/tmp/dashboard_speed.log", "a") as file:
        file.write(f"{message}\n")
        
            
            
class DashboardPage(VerticalScroll):
    """Landing page: system health, network, communications, services, recent events."""

    BINDINGS = [
        ("up", "cursor_up", "Scroll Up"),
        ("down", "cursor_down", "Scroll Down"),
    ]

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        # ---- System Data --------
        self.system = {}

        # ---- Network Data -------
        self.net = {}

        # ---- Communication ------
        self.coms = {}
        self.lcd = ""
        self.fc = ""
        self.atg = ""

        # ---- Functions ----------
        self.firewall = ""
        self.wireguard = ""
        self.ssh = ""
        self.data_monitor = ""

        # ---- Services -----------
        self.firewall_ser = ""
        self.wireguard_ser = ""
        self.ssh_ser = ""
        self.data_monitor_ser = ""

        # ---- WiFi ---------------
        self.wifi = {}
        self.status = ""
        self.hotspot = {}

        # ---- Cards --------------
        self.info_card = None
        self.system_card = None
        self.network_card = None
        self.coms_card = None
        self.service_card = None
        self.wifi_card = None
        self.hotspotcard = None
         
        self.load_dashboard_data()
        
                
    def load_dashboard_data(self):

        # ---- System Data --------
        self.system = system_service.get_system_status()

        # ---- Network Data -------
        self.net = network_service.get_network_summary()

        # ---- Communications -----
        self.coms = coms_service.get_devices()

        self.lcd = coms_service.get_device_status(self.coms.devices, "DET")
        self.fc = coms_service.get_device_status(self.coms.devices, "FC")
        self.atg = coms_service.get_atg_status()

        # ---- Functions ----------
        self.firewall = firewall_service.get_firewall_status()
        self.wireguard = wireguard_service.get_wireguard_status()
        self.ssh = ssh_service.get_ssh_status()
        self.data_monitor = network_service.get_data_usage_monitor_status()
        
        # ---- Services -----------
        self.firewall_ser = firewall_service.get_firewall_service()
        self.wireguard_ser = wireguard_service.get_wireguard_service()
        self.ssh_ser = ssh_service.get_ssh_service()
        self.data_monitor_ser = network_service.get_data_usage_monitor_service()

        # ---- WiFi ---------------
        self.wifi = wifi_service.get_wifi_status()
        self.status = ( "Connected" if self.wifi["connected"] else "Disconnected" )
        self.hotspot = wifi_service.get_hotspot_status()
                
                
    def compose(self):
            
        yield Static("[bold]Dashboard Test[/bold]", classes="page-title")
        
        self.info_card = StatusCard("Nano Information", [
            ("Hostname", self.system["hostname"]),
            ("Firmware", self.system["firmware"]),
        ])
        yield self.info_card
        

        with Horizontal(classes="card-row"):
            # System
            self.system_card = StatusCard("System Health", [
                ("CPU", self.system["cpu"]),
                ("RAM", self.system["ram"]),
                ("Storage", self.system["disk"]),
                ("Temperature", self.system["temperature"]),
                ("Up Time", self.system["uptime"]),
                ("Load", self.system["load"]),
            ])
            yield self.system_card

            # Network
            self.network_card = StatusCard("Network", [
                ("IP Address", self.net["ip_address"]),
                ("Internet", self.net["internet"]),
                ("WireGuard", self.wireguard),
                ("Firewall", self.firewall),
                ("SSH", self.ssh),
                ("Data Monitor", self.data_monitor),
            ])
            yield self.network_card

            # Coms
            self.coms_card = StatusCard("Communications", [
                ("LCD", self.lcd),
                ("Flow Controller", self.fc),
                ("ATG", self.atg),
                # ("Total Devices", str(len(self.coms.devices))),
            ])
            yield self.coms_card

            # Services
            self.service_card = StatusCard("Services (On Boot Startup)", [
                ("WireGuard", self.wireguard_ser),
                ("Firewall", self.firewall_ser),
                ("SSH", self.ssh_ser),
                ("Data Monitor", self.data_monitor_ser),
            ])
            yield self.service_card


        with Horizontal(classes="card-row"):
            
            # Wifi
            self.wifi_card = StatusCard("WiFi Settings",[
                ("Module", "Enabled" if self.wifi["enabled"] else "Disabled"),
                ("Status", self.status),
                ("SSID", self.wifi["ssid"]),
                ])
            yield self.wifi_card
            
            # Hotspot
            self.hotspotcard = StatusCard("Hotspot Settings",[
                ("Status", self.hotspot["status"]),
                ("Name", self.hotspot["name"]),
                ])
            yield self.hotspotcard

        
    def on_mount(self) -> None:

        # Do not block startup
        self.set_interval(5, self.refresh_fast_data)

        self.set_interval(20, self.refresh_medium_data)

        # Load dashboard after UI is visible
        self.set_timer(1, self.load_dashboard_data)
            
            
    def refresh_medium_data(self):
        
        # ------------------------
        # -- Refresh Fuctions ----
        # ------------------------        
        self.network_card.update_rows([
            ("IP Address", self.net["ip_address"]),
            ("Internet", self.net["internet"]),
            ("WireGuard", self.wireguard),
            ("Firewall", self.firewall),
            ("SSH", self.ssh),
            ("Data Monitor", self.data_monitor),
        ])

        # ------------------------
        # -- Refresh Services ----
        # ------------------------        
        self.service_card.update_rows([
            ("WireGuard", self.wireguard_ser),
            ("Firewall", self.firewall_ser),
            ("SSH", self.ssh_ser),
            ("Data Monitor", self.data_monitor_ser),
        ])
        
        
    def refresh_fast_data(self):
        
        self.load_dashboard_data()
            
        # ------------------------
        # ---Refresh Coms ----
        # ------------------------ 
        self.coms_card.update_rows([
            ("LCD", self.lcd),
            ("Flow Controller", self.fc),
            ("ATG", self.atg),
            # ("Total Devices", str(len(self.coms.devices))),
        ])

        # ------------------------
        # -- Refresh System ------
        # ------------------------    
        self.system_card.update_rows([
            ("CPU", self.system["cpu"]),
            ("RAM", self.system["ram"]),
            ("Disk", self.system["disk"]),
            ("Temperature", self.system["temperature"]),
            ("Up Time", self.system["uptime"]),
            ("Load", self.system["load"]),
        ])

        # ------------------------
        # ------- Wifi -----------
        # ------------------------ 
        self.wifi_card.update_rows([
            ("Module", "Enabled" if self.wifi["enabled"] else "Disabled"),
            ("Status", self.status),
            ("SSID", self.wifi["ssid"]),
            ])
        
        self.hotspotcard.update_rows([
            ("Status", self.hotspot["status"]),
            ("Name", self.hotspot["name"]),
            ])
        
        