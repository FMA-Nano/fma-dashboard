from textual.widgets import Static
from textual.widgets import Button, Input
from textual.containers import Horizontal, VerticalScroll
from textual.containers import ScrollableContainer
from textual import work

from widgets.pumps_config import PumpsConfig
from widgets.confirm_dialog import ConfirmDialog

from services import pumps_config as pumps_service



class PumpsConfigPage(ScrollableContainer):
    """compose() only builds an empty row - the actual per-pump Input
    forms are mounted once data comes back from a background worker, so
    this screen never blocks the UI thread waiting on the Nano/database.
    """

    BINDINGS = [
        ("tab", "next_field", "Next Field"),
        ("shift tab", "previous_field", "Previous Field"),
    ]


    def compose(self):

        yield Static( "[bold]Pump Configuration[/bold]", classes="page-title" )

        self.status = Static("Loading...", classes="info-block")
        yield self.status

        self.pump_row = Horizontal(classes="card-row")
        yield self.pump_row

        with Horizontal(classes="setting-actions"):
            yield Button("Save", id="save_pumps_config")

    def on_mount(self) -> None:
        self._loaded = False
        self._fetch_data()

    def on_show(self) -> None:
        # Reload the form if the user navigates back to this page, so it
        # reflects the latest values from the Nano (rather than possibly
        # stale edits from a previous visit).
        self._fetch_data()

    def force_refresh(self) -> None:
        """Immediately re-fetch, bypassing any visibility assumptions -
        used when the active Nano connection changes.
        """
        self._fetch_data()

    @work(thread=True, exclusive=True, group="pumps-config-page")
    def _fetch_data(self):
        pumps = pumps_service.get_pumps_config()
        self.app.call_from_thread(self._apply_data, pumps)

    def _apply_data(self, pumps):

        self.status.display = False

        # Remove any previously-mounted forms before rebuilding, so
        # revisiting the page doesn't stack duplicate Input widgets.
        for child in list(self.pump_row.children):
            child.remove()

        for pump in pumps:
            self.pump_row.mount(PumpsConfig(pump))

        self._loaded = True


    # --------------------------------
    # Save (with confirmation)
    # --------------------------------

    def on_button_pressed(self, event):

        if event.button.id == "save_pumps_config":
            self.save_clicked()

    def save_clicked(self):
        """Validate the form and, if there's anything to save, ask for
        confirmation before actually writing to the Nano.
        """

        pumps = pumps_service.get_pumps_config()

        pending_changes = []

        for pump in pumps:

            pump_id = pump["id"]
            hardware_id = self.query_one( f"#hardware_{pump_id}", Input ).value
            pulse_rate = self.query_one( f"#pulse_{pump_id}", Input ).value

            # Validate Hardware ID
            if not hardware_id.isdigit():
                self.notify( f"Pump {pump_id}: Hardware ID must be a number", severity="error" )
                return

            # Validate Pulse Rate
            try:
                pulse_rate = float(pulse_rate)
            except ValueError:
                self.notify( f"Pump {pump_id}: Pulse Rate must be a number", severity="error" )
                return

            # Check if changed
            if (
                int(hardware_id) != pump["HardwareId"]
                or
                pulse_rate != pump["PulsRate"]
            ):
                pending_changes.append((pump_id, int(hardware_id), pulse_rate))

        if not pending_changes:
            self.notify( "No changes detected", severity="information" )
            return

        count = len(pending_changes)
        message = f"Apply changes to {count} pump{'s' if count != 1 else ''} on the Nano?"

        self.app.push_screen(
            ConfirmDialog(message, title="Confirm Pump Changes", confirm_label="Save"),
            lambda confirmed: self._apply_changes(pending_changes) if confirmed else None,
        )

    def _apply_changes(self, pending_changes):

        # User-confirmed write, not a passive page load, so a brief
        # synchronous SSH round trip here is acceptable - it's already
        # what the person just explicitly asked to happen.
        changed = 0

        for pump_id, hardware_id, pulse_rate in pending_changes:

            success = pumps_service.update_pump_config(
                pump_id,
                hardware_id,
                pulse_rate
            )

            if success:
                changed += 1
            else:
                self.notify( f"Pump {pump_id} update failed", severity="error" )
                return

        self.notify( f"{changed} pump(s) updated. Waiting for sync...", severity="information" )
