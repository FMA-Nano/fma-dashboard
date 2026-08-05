from textual.containers import VerticalScroll
from textual.widgets import Static


from widgets.pumps_config import PumpsConfig

from services import pumps_config as pumps_service



class PumpsConfigPage(VerticalScroll):


    def compose(self):


        yield Static(
            "[bold]Pump Configuration[/bold]",
            classes="page-title"
        )


        pumps = pumps_service.get_pumps_config()


        for pump in pumps:

            yield PumpsConfig(pump)



    def on_button_pressed(self, event):


        if not event.button.id.startswith("apply_"):

            return



        pump_id = event.button.id.replace(
            "apply_",
            ""
        )



        hardware_id = self.query_one(
            f"#hardware_{pump_id}"
        ).value



        pulse_rate = self.query_one(
            f"#pulse_{pump_id}"
        ).value



        # Validate Hardware ID

        if not hardware_id.isdigit():

            self.notify(
                "Hardware ID must be a number",
                severity="error"
            )

            return



        # Validate Pulse Rate

        try:

            pulse_rate = float(
                pulse_rate
            )


        except ValueError:


            self.notify(
                "Pulse Rate must be a number",
                severity="error"
            )

            return



        success = pumps_service.update_pump_config(
            int(pump_id),
            int(hardware_id),
            pulse_rate
        )



        if success:


            self.notify(
                f"Pump {pump_id} updated. Waiting for sync...",
                severity="information"
            )


        else:


            self.notify(
                "Update failed",
                severity="error"
            )