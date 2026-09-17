from textual.containers import VerticalScroll
from textual.widgets import Static
from textual import work

from widgets.status_card import StatusCard
from services import system as system_service

LOADING = "Loading..."


class SystemPage(VerticalScroll):
    """Hardware status. compose() only builds placeholder widgets - the
    actual SSH fetch happens in a background worker, both for the initial
    load and every refresh, so this screen never blocks the UI thread
    (important since app.py mounts every screen up front at startup).
    """

    REFRESH_INTERVAL = 10

    def compose(self):

        yield Static("[bold]Controller Information[/bold]", classes="page-title")

        self.info_card = StatusCard("Nano Information", [
            ("Hostname", LOADING),
            ("Firmware", LOADING),
        ])
        yield self.info_card

        self.hardware_info_card = StatusCard("System Information", [
            ("CPU Model", LOADING),
            ("Architecture", LOADING),
            ("Serial", LOADING),
            ("Kernel", LOADING),
            ("OS", LOADING),
        ])
        yield self.hardware_info_card

        self.system_card = StatusCard("Hardware Status", [
            ("CPU", LOADING),
            ("RAM", LOADING),
            ("Disk", LOADING),
            ("Temperature", LOADING),
            ("Uptime", LOADING),
            ("Load", LOADING),
        ])
        yield self.system_card

    def on_mount(self) -> None:
        # Kick off an immediate fetch (non-blocking) so real data shows up
        # right after mount, then keep refreshing on the interval.
        self.refresh_data()
        self.set_interval(self.REFRESH_INTERVAL, self.refresh_data)

    def on_show(self) -> None:
        # Refresh right away when the user switches to this page, rather
        # than waiting for the next interval tick.
        self._fetch_data()

    def force_refresh(self) -> None:
        """Immediately re-fetch, bypassing the visibility check - used
        when the active Nano connection changes.
        """
        self._fetch_data()

    def refresh_data(self) -> None:
        if not self.display:
            return
        self._fetch_data()

    @work(thread=True, exclusive=True, group="system-page")
    def _fetch_data(self) -> None:
        system = system_service.get_system_status()
        self.app.call_from_thread(self._apply_data, system)

    def _apply_data(self, system) -> None:
        self.info_card.update_rows([
            ("Hostname", system["hostname"]),
            ("Firmware", system["firmware"]),
        ])

        self.hardware_info_card.update_rows([
            ("CPU Model", system["cpu_model"]),
            ("Architecture", system["architecture"]),
            ("Serial", system["serial"]),
            ("Kernel", system["kernel"]),
            ("OS", system["os"]),
        ])

        self.system_card.update_rows([
            ("CPU", system["cpu"]),
            ("RAM", system["ram"]),
            ("Disk", system["disk"]),
            ("Temperature", system["temperature"]),
            ("Uptime", system["uptime"]),
            ("Load", system["load"]),
        ])
