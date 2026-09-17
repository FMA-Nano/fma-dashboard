from textual.widgets import Static, Button
from textual.containers import Horizontal, Vertical
from textual.message import Message
from version import VERSION

LOGO = f"""[bold #4FA8E0]
███████╗███╗   ███╗ █████╗
██╔════╝████╗ ████║██╔══██╗
█████╗  ██╔████╔██║███████║
██╔══╝  ██║╚██╔╝██║██╔══██║[/]
[bold white]Fuel Management Africa[/]  [dim]— Device Maintenance Console[/dim]
[dim]Dashboard Version {VERSION}[/dim]
"""


class AppHeader(Horizontal):
    """Compact branded header shown above the sidebar/content split.

    Two labeled rows, docked top-right, reachable from any screen:

        Nano (Refresh / Disconnect / Restart) - Refresh forces every
        screen to re-fetch immediately (bypassing each screen's own
        10s/20s/60s timers); Restart here reboots the Nano itself (the
        device the dashboard is connected to).

        Software (Restart / Stop All) - controls the ST500V3 controller
        software running on the Nano, mirroring two options from the
        Nano's own on-device admin menu. This Restart runs the
        controller's own restart script, distinct from the Nano-level
        reboot above.
    """

    class DisconnectRequested(Message):
        """Bubbles up to the App when the Disconnect button is pressed."""

    class RefreshRequested(Message):
        """Bubbles up to the App when the Refresh button is pressed."""

    class RebootNanoRequested(Message):
        """Bubbles up to the App when the Nano row's Restart button is pressed."""

    class RestartSoftwareRequested(Message):
        """Bubbles up to the App when the Software row's Restart button is pressed."""

    class StopAllSoftwareRequested(Message):
        """Bubbles up to the App when the Stop All button is pressed."""

    def __init__(self):
        super().__init__(id="app-header")

    def compose(self):
        yield Static(LOGO, id="app-header-logo")
        yield Static(
            "⚠ Lost connection to Nano - reconnecting...",
            id="nano-disconnect-banner",
        )
        with Vertical(id="header-actions"):
            with Vertical(classes="header-group"):
                yield Static("Nano", classes="header-group-label")
                with Horizontal(classes="header-actions-row"):
                    yield Button("Refresh", id="refresh_button")
                    yield Button("Disconnect", id="disconnect_button")
                    yield Button("Restart", id="reboot_nano_button")
            with Vertical(classes="header-group"):
                yield Static("Software", classes="header-group-label")
                with Horizontal(classes="header-actions-row"):
                    yield Button("Restart", id="restart_software_button")
                    yield Button("Stop All", id="stop_all_software_button")

    def on_button_pressed(self, event):
        if event.button.id == "disconnect_button":
            self.post_message(self.DisconnectRequested())
        elif event.button.id == "refresh_button":
            self.post_message(self.RefreshRequested())
        elif event.button.id == "reboot_nano_button":
            self.post_message(self.RebootNanoRequested())
        elif event.button.id == "restart_software_button":
            self.post_message(self.RestartSoftwareRequested())
        elif event.button.id == "stop_all_software_button":
            self.post_message(self.StopAllSoftwareRequested())

    def set_disconnected_banner(self, visible: bool) -> None:
        """Show or hide the persistent "Lost connection" banner. Unlike
        a toast notification, this stays up for exactly as long as told
        to - it doesn't auto-dismiss on its own, so it stays visible for
        the entire outage rather than fading after a few seconds while
        the Nano might still be unreachable.
        """
        self.query_one("#nano-disconnect-banner").display = visible
