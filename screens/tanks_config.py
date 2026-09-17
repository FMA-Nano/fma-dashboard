from textual.widgets import Static, Input, Button
from textual.containers import Horizontal, ScrollableContainer
from textual import work

from widgets.tanks_config import TanksConfig
from widgets.confirm_dialog import ConfirmDialog

from services import tanks_config as tanks_service


class TanksConfigPage(ScrollableContainer):
    """compose() only builds an empty row - the actual per-tank Input
    forms are mounted once data comes back from a background worker, so
    this screen never blocks the UI thread waiting on the Nano/database.
    """

    BINDINGS = [
        ("tab", "next_field", "Next Field"),
        ("shift tab", "previous_field", "Previous Field"),
    ]


    def compose(self):

        yield Static(
            "[bold]Tank Configuration[/bold]",
            classes="page-title"
        )

        self.status = Static("Loading...", classes="info-block")
        yield self.status

        self.tank_row = Horizontal(classes="card-row")
        yield self.tank_row

        with Horizontal(classes="setting-actions"):
            yield Button("Save", id="save_tanks_config")

    def on_mount(self) -> None:
        self._fetch_data()

    def on_show(self) -> None:
        # Reload the form if the user navigates back to this page, so it
        # reflects the latest values from the Nano.
        self._fetch_data()

    def force_refresh(self) -> None:
        """Immediately re-fetch - used when the active Nano connection
        changes.
        """
        self._fetch_data()

    @work(thread=True, exclusive=True, group="tanks-config-page")
    def _fetch_data(self):
        tanks = tanks_service.get_tanks_config()
        self.app.call_from_thread(self._apply_data, tanks)

    def _apply_data(self, tanks):

        self.status.display = False

        for child in list(self.tank_row.children):
            child.remove()

        for tank in tanks:
            self.tank_row.mount(TanksConfig(tank))


    # --------------------------------
    # Save (with confirmation)
    # --------------------------------

    def on_button_pressed(self, event):

        if event.button.id == "save_tanks_config":
            self.save_clicked()

    def save_clicked(self):
        """Validate the form and, if there's anything to save, ask for
        confirmation before actually writing to the Nano.
        """

        tanks = tanks_service.get_tanks_config()

        pending_changes = []

        for tank in tanks:

            tank_id = tank["id"]
            tank_no = tank["TankNo"]

            probe_id = self.query_one(
                f"#probe_{tank_id}",
                Input
            ).value

            if not probe_id.isdigit():
                self.notify(
                    f"Tank {tank_no}: Probe ID must be a number",
                    severity="error"
                )
                return

            if int(probe_id) != tank["ProbeId"]:
                pending_changes.append((tank_id, tank_no, int(probe_id)))

        if not pending_changes:
            self.notify("No changes detected", severity="information")
            return

        count = len(pending_changes)
        message = f"Apply changes to {count} tank{'s' if count != 1 else ''} on the Nano?"

        self.app.push_screen(
            ConfirmDialog(message, title="Confirm Tank Changes", confirm_label="Save"),
            lambda confirmed: self._apply_changes(pending_changes) if confirmed else None,
        )

    def _apply_changes(self, pending_changes):

        # User-confirmed write, not a passive page load, so a brief
        # synchronous SSH round trip here is acceptable - it's already
        # what the person just explicitly asked to happen.
        changed = 0

        for tank_id, tank_no, probe_id in pending_changes:

            success = tanks_service.update_tank_config(
                tank_id,
                probe_id
            )

            if success:
                changed += 1
            else:
                self.notify(
                    f"Tank {tank_no} update failed",
                    severity="error"
                )
                return

        self.notify(
            f"{changed} tank(s) updated. Waiting for sync...",
            severity="information"
        )
