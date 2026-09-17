from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Static
from textual import work


from widgets.status_card import StatusCard


from services import pumps as pumps_service
from services import tanks as tanks_service


REFRESH_INTERVAL = 10


class PumpsPage(VerticalScroll):
    """compose() only builds the page skeleton (empty pump/tank rows) -
    the actual pump/tank cards are created once data comes back from a
    background worker, both on initial mount and every refresh, so this
    screen never blocks the UI thread waiting on the Nano/database.
    """

    BINDINGS = [
        ("up", "cursor_up", "Scroll Up"),
        ("down", "cursor_down", "Scroll Down"),
    ]

    def compose(self):

        self.tank_cards = {}
        self.pump_cards = {}

        yield Static( "[bold]Pumps[/bold]", classes="page-title" )
        self.pump_row = Horizontal(classes="card-row")
        yield self.pump_row

        yield Static( "[bold]Tanks[/bold]", classes="page-title" )
        self.tank_row = Horizontal(classes="card-row")
        yield self.tank_row

    def on_mount(self):
        self.refresh_data()
        self.set_interval(REFRESH_INTERVAL, self.refresh_data)

    def on_show(self) -> None:
        # Refresh right away when the user switches to this page.
        self._fetch_data()

    def force_refresh(self) -> None:
        """Immediately re-fetch, bypassing the visibility check - used
        when the active Nano connection changes.
        """
        self._fetch_data()

    def refresh_data(self):
        if not self.display:
            return
        self._fetch_data()

    @work(thread=True, exclusive=True, group="pumps-page")
    def _fetch_data(self):

        tanks = tanks_service.get_tanks()
        pumps = pumps_service.get_pumps()

        self.app.call_from_thread(self._apply_data, tanks, pumps)

    def _apply_data(self, tanks, pumps):

        # First pass ever: build a card for each pump/tank and mount it.
        # Subsequent passes: just update rows on the cards we already have,
        # so we don't destroy/rebuild widgets (and lose scroll position,
        # flicker, etc) every refresh unless the set of pumps/tanks
        # actually changed.

        tank_ids_now = {tank.id for tank in tanks}
        pump_ids_now = {pump.id for pump in pumps}

        for tank in tanks:
            if tank.id in self.tank_cards:
                self.tank_cards[tank.id].update_rows(self.get_tank_rows(tank))
            else:
                card = StatusCard(f"Tank {tank.tank_number}", self.get_tank_rows(tank))
                self.tank_cards[tank.id] = card
                self.tank_row.mount(card)

        for pump in pumps:
            if pump.id in self.pump_cards:
                self.pump_cards[pump.id].update_rows(self.get_pump_rows(pump))
            else:
                card = StatusCard(f"Pump {pump.hardware_id}", self.get_pump_rows(pump))
                self.pump_cards[pump.id] = card
                self.pump_row.mount(card)

        # Remove cards for pumps/tanks that no longer exist in the latest
        # fetch - most importantly after switching to a different Nano
        # with fewer pumps/tanks than the previous one, where otherwise
        # the extra old card(s) would just stay on screen forever since
        # the loops above only ever add or update, never delete.
        for tank_id in list(self.tank_cards.keys()):
            if tank_id not in tank_ids_now:
                self.tank_cards.pop(tank_id).remove()

        for pump_id in list(self.pump_cards.keys()):
            if pump_id not in pump_ids_now:
                self.pump_cards.pop(pump_id).remove()



    def get_tank_rows(self, tank):

        if tank.enabled:
            return [
                ( "Enabled       ", "[#5FD68A]Yes[/#5FD68A]" ),
                ( "Capacity      ", f"{tank.capacity} L" ),
                ( "Volume        ", f"[#5FD68A]{tank.volume:.1f} L[/#5FD68A]" ),
                ( "Ullage        ", f"{tank.ullage:.1f} L" ),
                ( "Level         ", f"[#d1ce00]{tank.level} mm[/#d1ce00]" ),
                ( "Temperature   ", f"[#E05C5C]{tank.temperature:.1f} °C[/#E05C5C]" ),
                ( "Water         ", f"[#00fff7]{tank.water:.1f} mm[/#00fff7]" ),
                ( "Probe         ", str(tank.probe_id) ),
            ]

        else:
            return [
                ( "Enabled       ", "No" ),
                ( "Capacity      ", f"{tank.capacity} L" ),
                ( "Volume        ", f"{tank.volume:.1f} L" ),
                ( "Ullage        ", f"{tank.ullage:.1f} L" ),
                ( "Level         ", f"{tank.level} mm" ),
                ( "Temperature   ", f"{tank.temperature:.1f} °C" ),
                ( "Water         ", f"{tank.water:.1f} mm" ),
                ( "Probe         ", str(tank.probe_id) ),
            ]


    def get_pump_rows(self, pump):

        return [
            ( "Status", pump.status_text ),
            ( "Pulse Rate", str(pump.pulse_rate) ),
            ( "Timeout", str(pump.pulse_timeout) ),
            ( "Auto Auth", str(pump.auto_authorize) ),
            ( "Hardware ID", str(pump.hardware_id) ),
            ( "Tank", str(pump.linked_tank) ),
        ]
