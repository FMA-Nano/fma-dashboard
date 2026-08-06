from textual.widgets import Static
from textual.widgets import Button, Input
from textual.containers import Horizontal, VerticalScroll
from textual.containers import ScrollableContainer

from widgets.pumps_config import PumpsConfig

from services import pumps_config as pumps_service



class PumpsConfigPage(ScrollableContainer):

    BINDINGS = [
        ("f2", "apply", "Apply"),
        ("tab", "next_field", "Next Field"),
        ("shift tab", "previous_field", "Previous Field"),
    ]
        

    def compose(self):
        
        yield Static( "[bold]Pump Configuration[/bold]", classes="page-title" )
        
        with Horizontal(classes="card-row"):

            pumps = pumps_service.get_pumps_config()

            for pump in pumps:
                yield PumpsConfig(pump)
                
        
    def action_apply(self):

        self.apply_changes()

    def apply_changes(self):

        pumps = pumps_service.get_pumps_config()

        changed = 0

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

                success = pumps_service.update_pump_config(
                    pump_id,
                    int(hardware_id),
                    pulse_rate
                )


                if success:
                    changed += 1

                else:
                    self.notify( f"Pump {pump_id} update failed", severity="error" )

                    return



        if changed:

            self.notify( f"{changed} pump(s) updated. Waiting for sync...", severity="information" )

        else:

            self.notify( "No changes detected", severity="information" )
                

    def on_button_pressed(self, event):

        if event.button.id == "apply_all":

            self.apply_changes()