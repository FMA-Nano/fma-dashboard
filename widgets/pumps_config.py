from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Input


class PumpsConfig(Vertical):

    def __init__(self, pump, id=None):

        super().__init__(
            id=id,
            classes="pump-config-card"
        )

        self.pump = pump


    def compose(self):

        yield Static(
            f"[bold]Pump {self.pump['id']}[/bold]",
            classes="pump-title"
        )


        with Horizontal(classes="config-row"):

            yield Static(
                "Hardware ID",
                classes="config-label"
            )

            yield Input(
                str(self.pump["HardwareId"]),
                id=f"hardware_{self.pump['id']}",
                classes="config-input"
            )


        with Horizontal(classes="config-row"):

            yield Static(
                "Pulse Rate",
                classes="config-label"
            )

            yield Input(
                str(self.pump["PulsRate"]),
                id=f"pulse_{self.pump['id']}",
                classes="config-input"
            )