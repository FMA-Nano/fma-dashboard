from textual.widgets import Static, Input
from textual.containers import Horizontal, ScrollableContainer

from widgets.tanks_config import TanksConfig

from services import tanks_config as tanks_service


class TanksConfigPage(ScrollableContainer):

    BINDINGS = [
        ("f2", "apply", "Apply"),
        ("tab", "next_field", "Next Field"),
        ("shift tab", "previous_field", "Previous Field"),
    ]


    def action_apply(self):

        self.apply_changes()


    def apply_changes(self):

        tanks = tanks_service.get_tanks_config()

        changed = 0

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

                success = tanks_service.update_tank_config(
                    tank_id,
                    int(probe_id)
                )

                if success:

                    changed += 1

                else:

                    self.notify(
                        f"Tank {tank_no} update failed",
                        severity="error"
                    )

                    return


        if changed:

            self.notify(
                f"{changed} tank(s) updated. Waiting for sync...",
                severity="information"
            )

        else:

            self.notify(
                "No changes detected",
                severity="information"
            )


    def compose(self):

        yield Static(
            "[bold]Tank Configuration[/bold]",
            classes="page-title"
        )

        with Horizontal(classes="card-row"):

            tanks = tanks_service.get_tanks_config()

            for tank in tanks:

                yield TanksConfig(tank)


    def on_button_pressed(self, event):

        if event.button.id == "apply_all":

            self.apply_changes()