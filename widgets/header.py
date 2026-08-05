from textual.widgets import Static
from textual.containers import Vertical
from version import VERSION

LOGO = f"""[bold #4FA8E0]
███████╗███╗   ███╗ █████╗
██╔════╝████╗ ████║██╔══██╗
█████╗  ██╔████╔██║███████║
██╔══╝  ██║╚██╔╝██║██╔══██║
██║     ██║ ╚═╝ ██║██║  ██║[/]
[bold white]Fuel Management Africa[/]  [dim]— Device Maintenance Console[/dim]
[dim]Dashboard Version {VERSION}[/dim]
"""


class AppHeader(Static):
    """Compact branded header shown above the sidebar/content split."""

    def __init__(self):
        super().__init__(LOGO, id="app-header")

    def compose(self):
        return []
