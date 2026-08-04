from typing import List, Tuple

from textual.containers import VerticalScroll
from textual.widgets import Static
from widgets.status_card import StatusCard
from services import system as system_service
from services.refresh import refresh_manager


class SystemPage(VerticalScroll):
    def compose(self):
        system = system_service.get_system_status()
        
        yield Static("[bold]Controller Information[/bold]", classes="page-title")
        
        self.info_card = StatusCard("Nano Information", [
            ("Hostname", system["hostname"]),
            ("Firmware", system["firmware"]),
        ])
        yield self.info_card
        
        self.info_card = StatusCard("System Information", [
            ("CPU Model", system["cpu_model"]),
            ("Architecture", system["architecture"]),
            ("Serial", system["serial"]),
            ("Kernel", system["kernel"]),
            ("OS", system["os"]),
        ])
        yield self.info_card
        
        self.system_card = StatusCard("Hardware Status", [
            ("CPU", system["cpu"]),
            ("RAM", system["ram"]),
            ("Disk", system["disk"]),
            ("Temperature", system["temperature"]),
            ("Uptime", system["uptime"]),
            ("Load", system["load"]),
        ])
        yield self.system_card



    def on_mount(self) -> None:
        refresh_manager.register(self.refresh_data)

    def refresh_data(self) -> None:
        system = system_service.get_system_status()

        self.system_card.update_rows([
            ("CPU", system["cpu"]),
            ("RAM", system["ram"]),
            ("Disk", system["disk"]),
            ("Temperature", system["temperature"]),
            ("Uptime", system["uptime"]),
            ("Load", system["load"]),
        ])

