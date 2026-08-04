from textual.containers import VerticalScroll
from textual.widgets import Static

from widgets.header import LOGO


class AboutPage(VerticalScroll):
    def compose(self):
        yield Static("[bold]About[/bold]", classes="page-title")
        yield Static(LOGO)
        yield Static(
            "Version        0.2\n"
            "Date Updated   04-07-2026\n"
            "Build          dev\n"
            "Vendor         Fuel Management Africa\n",
            classes="info-block",
        )
