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
    


    def action_apply(self):

        widget = self.app.focused

        if widget is None:
            return

        # If focus is on Hardware ID or Pulse Rate
        if isinstance(widget, Input):

            if widget.id.startswith("hardware_"):
                pump_id = widget.id.replace("hardware_", "")
            elif widget.id.startswith("pulse_"):
                pump_id = widget.id.replace("pulse_", "")
            else:
                return

            button = self.query_one(
                f"#apply_{pump_id}",
                Button
            )
            button.press()


        # If focus is already on Apply button
        elif isinstance(widget, Button):

            if widget.id.startswith("apply_"):
                widget.press()
            
            
    def compose(self):
        
        yield Static( "[bold]Pump Configuration[/bold]", classes="page-title" )
        
        with Horizontal(classes="card-row"):

            pumps = pumps_service.get_pumps_config()

            for pump in pumps:
                yield PumpsConfig(pump)



    def on_button_pressed(self, event):

        if not event.button.id.startswith("apply_"):
            return

        pump_id = event.button.id.replace( "apply_", "" )
        hardware_id = self.query_one( f"#hardware_{pump_id}" ).value
        pulse_rate = self.query_one( f"#pulse_{pump_id}" ).value

        # Validate Hardware ID
        if not hardware_id.isdigit():
            self.notify( "Hardware ID must be a number", severity="error" )
            return

        # Validate Pulse Rate
        try:
            pulse_rate = float( pulse_rate )

        except ValueError:
            self.notify( "Pulse Rate must be a number", severity="error" )
            return


        success = pumps_service.update_pump_config(
            int(pump_id),
            int(hardware_id),
            pulse_rate
        )

        if success:
            self.notify( f"Pump {pump_id} updated. Waiting for sync...", severity="information"
            )
        else:
            self.notify("Update failed", severity="error" )