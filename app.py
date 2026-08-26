from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, ContentSwitcher

from widgets.header import AppHeader
from widgets.sidebar import Sidebar
from widgets.loadingScreen import LoadingScreen


class NanoDashboard(App):

    TITLE = "Fuel Management Africa - Device Maintenance Console"
    CSS_PATH = "dashboard.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "focus_sidebar", "Back"),
        ("enter", "select_cursor", "Open"),
    ]

    def compose(self) -> ComposeResult:
        # First thing shown
        yield LoadingScreen(id="loading")


    def on_mount(self):

        # Give Textual time to draw loading screen
        self.set_timer(
            0.5,
            self.load_main_ui
        )

    def load_main_ui(self):

        # Remove loading screen
        loading = self.query_one("#loading")
        loading.remove()

        # Build real interface
        self.mount( AppHeader() )

        body = Horizontal( id="body" )

        self.mount( body )

        sidebar = Sidebar()

        body.mount( sidebar )

        content = ContentSwitcher( initial="dashboard", id="content" )

        body.mount( content )


        # Import here so startup is faster
        from screens.dashboard import DashboardPage
        from screens.system import SystemPage
        from screens.network import NetworkPage
        from screens.pumps import PumpsPage
        from screens.security import SecurityPage
        from screens.cronjobs import CronJobPage
        from screens.pumps_config import PumpsConfigPage
        from screens.tanks_config import TanksConfigPage
        from screens.about import AboutPage

        content.mount( DashboardPage(id="dashboard") )
        content.mount( SystemPage(id="system") )
        content.mount( NetworkPage(id="network") )
        content.mount( PumpsPage(id="pumps") )
        content.mount( PumpsConfigPage(id="pumps_config") )
        content.mount( TanksConfigPage(id="tanks_config") )
        content.mount( SecurityPage(id="security") )
        content.mount( CronJobPage(id="cronjobs") )
        content.mount( AboutPage(id="about") )

        self.mount( Footer() )


    # --------------------------
    # Sidebar
    # --------------------------
    def action_focus_sidebar(self):
        sidebar = self.query_one( Sidebar )
        sidebar.focus()


    # --------------------------
    # Page switching
    # --------------------------
    def on_sidebar_nav_selected(
        self,
        message: Sidebar.NavSelected
    ):

        switcher = self.query_one( "#content", ContentSwitcher )
        switcher.current = message.key
        switcher.visible_content.focus()


if __name__ == "__main__":

    NanoDashboard().run()