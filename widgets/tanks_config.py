from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Input


class TanksConfig(Vertical):

    def __init__(self, tank, id=None):

        super().__init__(
            id=id,
            classes="pump-config-card"
        )

        self.tank = tank


    def compose(self):

        yield Static(
            f"[bold]Tank {self.tank['TankNo']}[/bold]",
            classes="pump-title"
        )


        with Horizontal(classes="config-row"):

            yield Static(
                "Probe ID",
                classes="config-label"
            )

            yield Input(
                str(self.tank["ProbeId"]),
                id=f"probe_{self.tank['id']}",
                classes="config-input"
            )