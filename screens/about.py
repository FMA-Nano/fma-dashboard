from textual.containers import VerticalScroll
from textual.widgets import Static

from widgets.header import LOGO
from version import VERSION, BUILD, DATE_UPDATED, VENDOR


class AboutPage(VerticalScroll):

    def compose(self):

        yield Static(
            "[bold]About[/bold]",
            classes="page-title"
        )

        yield Static(LOGO)

        yield Static(
            f"Version        {VERSION}\n"
            f"Date Updated   {DATE_UPDATED}\n"
            f"Build          {BUILD}\n"
            f"Vendor         {VENDOR}\n",
            classes="info-block",
        )