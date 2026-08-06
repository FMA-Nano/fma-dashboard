from startup import run_startup

run_startup()


from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, ContentSwitcher

from widgets.header import AppHeader
from widgets.sidebar import Sidebar

from screens.dashboard import DashboardPage
from screens.system import SystemPage
from screens.network import NetworkPage
from screens.pumps import PumpsPage
from screens.logs import LogsPage
from screens.settings import SettingsPage
from screens.about import AboutPage
from screens.security import SecurityPage
from screens.cronjobs import CronJobPage
from screens.pumps_config import PumpsConfigPage

class NanoDashboard(App):
    """Fuel Management Africa - Device Maintenance Console."""

    TITLE = "Fuel Management Africa - Device Maintenance Console"
    CSS_PATH = "dashboard.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "focus_sidebar", "Back"),
        ("enter", "select_cursor", "Open"),
    ]


    def compose(self) -> ComposeResult:

        yield AppHeader()

        with Horizontal(id="body"):

            yield Sidebar()

            with ContentSwitcher(
                initial="dashboard",
                id="content"
            ):

                yield DashboardPage(id="dashboard")
                yield SystemPage(id="system")
                yield NetworkPage(id="network")
                yield PumpsPage(id="pumps")
                yield PumpsConfigPage(id="pumps_config")
                yield SecurityPage(id="security")
                yield CronJobPage(id="cronjobs")
                # yield LogsPage(id="logs")
                # yield SettingsPage(id="settings")
                yield AboutPage(id="about")


        yield Footer()



    # --------------------------
    # App Actions
    # --------------------------


    def action_focus_sidebar(self):

        sidebar = self.query_one(
            Sidebar
        )

        sidebar.focus()

    # --------------------------
    # Page Switching
    # --------------------------


    def on_sidebar_nav_selected(
        self,
        message: Sidebar.NavSelected
    ):

        switcher = self.query_one(
            "#content",
            ContentSwitcher
        )


        switcher.current = message.key


        switcher.visible_content.focus()



if __name__ == "__main__":

    NanoDashboard().run()