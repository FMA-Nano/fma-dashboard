import os

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, ContentSwitcher
from textual import work

from widgets.header import AppHeader
from widgets.sidebar import Sidebar
from widgets.loadingScreen import LoadingScreen
from widgets.login_screen import LoginScreen
from widgets.confirm_dialog import ConfirmDialog

from services import config as nano_config
from services import system as system_service
from services.remote import close_connection, run_remote


class NanoDashboard(App):

    TITLE = "Fuel Management Africa - Device Maintenance Console"
    CSS_PATH = "dashboard.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "focus_sidebar", "Back"),
        ("enter", "select_cursor", "Open"),
    ]

    # Connectivity watchdog: starts checking every MIN_INTERVAL seconds;
    # each consecutive failure doubles the wait (up to MAX_INTERVAL) so a
    # genuinely offline Nano isn't hammered with checks forever. The
    # instant a check succeeds after having failed, every screen is
    # force-refreshed and the interval resets back to MIN_INTERVAL.
    NANO_CHECK_MIN_INTERVAL = 8
    NANO_CHECK_MAX_INTERVAL = 60

    def compose(self) -> ComposeResult:
        # First thing shown
        yield LoadingScreen(id="loading")


    def on_mount(self):

        # Give Textual time to draw loading screen
        self.set_timer(
            0.5,
            self.after_loading
        )

    def after_loading(self):

        loading = self.query_one("#loading")
        loading.remove()

        # A previously-saved connection means this machine has already
        # been pointed at a Nano before - skip straight to the main UI.
        # A fresh machine (no saved connection file) needs to be told
        # which Nano to talk to before anything else is useful.
        if os.path.exists(nano_config.CONFIG_FILE):
            self.load_main_ui()
        else:
            self.push_screen(LoginScreen(), self._on_login_dismissed)

    def _on_login_dismissed(self, connected: bool) -> None:
        """Called when the login modal closes, whether by a successful
        Connect or by Skip.

        `connected` is only used to decide whether the main UI needs
        building for the first time, vs already existing and just
        needing its data refreshed after a reconnect/disconnect.
        """

        if self.query("#content"):
            # Main UI already exists (this was a Disconnect -> reconnect
            # cycle, not first launch) - refresh everything so no stale
            # data from the previous Nano lingers anywhere, and let the
            # watchdog know we're (hopefully) back online.
            self._nano_online = True
            self._nano_check_interval = self.NANO_CHECK_MIN_INTERVAL
            self.refresh_all_screens()
        else:
            self.load_main_ui()

    def load_main_ui(self):

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
        from screens.data_usage import DataUsagePage
        from screens.log_files import LogFilesPage
        from screens.pumps import PumpsPage
        from screens.security import SecurityPage
        from screens.cronjobs import CronJobPage
        from screens.pumps_config import PumpsConfigPage
        from screens.tanks_config import TanksConfigPage
        from screens.settings import SettingsPage
        from screens.router_settings import RouterSettingsPage
        from screens.about import AboutPage

        content.mount( DashboardPage(id="dashboard") )
        content.mount( SystemPage(id="system") )
        content.mount( NetworkPage(id="network") )
        content.mount( DataUsagePage(id="data_usage") )
        content.mount( LogFilesPage(id="log_files") )
        content.mount( PumpsPage(id="pumps") )
        content.mount( PumpsConfigPage(id="pumps_config") )
        content.mount( TanksConfigPage(id="tanks_config") )
        content.mount( SecurityPage(id="security") )
        content.mount( CronJobPage(id="cronjobs") )
        content.mount( SettingsPage(id="settings") )
        content.mount( RouterSettingsPage(id="router_settings") )
        content.mount( AboutPage(id="about") )

        self.mount( Footer() )

        self.start_nano_watchdog()


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


    # --------------------------
    # Manual refresh
    # --------------------------
    def on_app_header_refresh_requested(
        self,
        message: AppHeader.RefreshRequested,
    ) -> None:

        self.refresh_all_screens()
        self.notify("Refreshing all screens...", severity="information")

    # --------------------------
    # Nano reboot (top-right header)
    # --------------------------
    def on_app_header_reboot_nano_requested(
        self,
        message: AppHeader.RebootNanoRequested,
    ) -> None:

        def handle_result(confirmed: bool):
            if confirmed:
                self.notify("Rebooting the Nano...", severity="warning")
                self._reboot_nano_worker()

        self.push_screen(
            ConfirmDialog(
                "Reboot the Nano?\n\n"
                "This reboots the device itself - the dashboard will "
                "lose connection briefly and reconnect automatically "
                "once it's back up.",
                title="Reboot Nano?",
                confirm_label="Restart",
            ),
            handle_result,
        )

    @work(thread=True, exclusive=True, group="nano-reboot")
    def _reboot_nano_worker(self) -> None:
        system_service.reboot_nano()

    # --------------------------
    # Software control (Restart / Stop All)
    # --------------------------
    def on_app_header_restart_software_requested(
        self,
        message: AppHeader.RestartSoftwareRequested,
    ) -> None:

        def handle_result(confirmed: bool):
            if confirmed:
                self.notify("Restarting software...", severity="information")
                self._run_software_action(system_service.restart_software)

        self.push_screen(
            ConfirmDialog(
                "Restart the ST500V3 controller software?\n\n"
                "Runs ./bin/restart.sh on the Nano.",
                title="Restart Software?",
                confirm_label="Restart",
            ),
            handle_result,
        )

    def on_app_header_stop_all_software_requested(
        self,
        message: AppHeader.StopAllSoftwareRequested,
    ) -> None:

        def handle_result(confirmed: bool):
            if confirmed:
                self.notify("Stopping all software...", severity="warning")
                self._run_software_action(system_service.stop_all_software)

        self.push_screen(
            ConfirmDialog(
                "Stop ALL Python processes on the Nano?\n\n"
                "This stops the main controller software immediately "
                "(sudo killall python) - it will not restart on its own "
                "unless something else brings it back up. Use Restart "
                "afterward if you need it running again.",
                title="Stop All Software?",
                confirm_label="Stop All",
            ),
            handle_result,
        )

    @work(thread=True, exclusive=True, group="software-action")
    def _run_software_action(self, action) -> None:
        success, output = action()
        self.call_from_thread(self._show_software_action_result, success, output)

    def _show_software_action_result(self, success: bool, output: str) -> None:
        if success:
            self.notify(output.strip()[:200] or "Done.", severity="information")
        else:
            self.notify(f"Failed: {output.strip()[:200]}", severity="error")


    # --------------------------
    # Disconnect / reconnect
    # --------------------------
    def on_app_header_disconnect_requested(
        self,
        message: AppHeader.DisconnectRequested,
    ) -> None:

        # Tear down the current connection and stop treating it as
        # active - if the user hits Skip on the reconnect modal without
        # entering a new Nano, calls should fail cleanly (empty host)
        # rather than silently continuing to talk to the old one.
        try:
            close_connection()
        except Exception:
            pass

        nano_config.set_nano(host="", port=22, user="pi", password="")

        # Don't auto-skip the login gate on next launch until a new
        # connection is actually established and saved.
        try:
            if os.path.exists(nano_config.CONFIG_FILE):
                os.remove(nano_config.CONFIG_FILE)
        except Exception:
            pass

        # Reset watchdog state - nothing to check until reconnected.
        self._nano_online = None

        # This is a deliberate disconnect, not an outage - clear any
        # stale "lost connection" banner so it doesn't linger through
        # the reconnect flow.
        header_matches = self.query(AppHeader)
        if header_matches:
            header_matches.first().set_disconnected_banner(False)

        # Immediately clear stale data from every screen so nothing from
        # the old Nano is left showing while the modal is up.
        self.refresh_all_screens()

        self.push_screen(LoginScreen(), self._on_login_dismissed)

    def refresh_all_screens(self) -> None:
        """Force every mounted page to re-fetch its data right away,
        bypassing their normal visibility checks - used whenever the
        active Nano connection changes, so no stale data from a
        previous connection lingers anywhere in the app.
        """
        matches = self.query("#content")

        if not matches:
            return

        content = matches.first()

        for child in content.children:
            if hasattr(child, "force_refresh"):
                child.force_refresh()


    # --------------------------
    # Connectivity watchdog (auto-reconnect detection)
    # --------------------------
    def start_nano_watchdog(self) -> None:
        """Begin periodically checking whether the Nano is reachable in
        the background. On the transition from unreachable -> reachable,
        every screen is force-refreshed immediately rather than waiting
        for its own next scheduled refresh (which could be up to a
        minute away).
        """
        self._nano_online = None  # unknown until the first check runs
        self._nano_check_interval = self.NANO_CHECK_MIN_INTERVAL
        self._schedule_next_nano_check()

    def _schedule_next_nano_check(self) -> None:
        self.set_timer(self._nano_check_interval, self._run_nano_check)

    def _run_nano_check(self) -> None:

        # Don't probe while a modal (login/confirm dialog) is up - the
        # person is mid-action, and while the login modal specifically is
        # open the "active" connection may be empty/in-flux anyway.
        if len(self.screen_stack) > 1:
            self._schedule_next_nano_check()
            return

        conn = nano_config.get_nano()

        if not conn.get("host"):
            # Nothing configured (e.g. right after Disconnect) - nothing
            # to check yet.
            self._schedule_next_nano_check()
            return

        self._nano_check_worker()

    @work(thread=True, exclusive=True, group="nano-watchdog")
    def _nano_check_worker(self) -> None:
        result = run_remote(["true"], timeout=5)
        self.call_from_thread(self._apply_nano_check_result, result.ok)

    def _apply_nano_check_result(self, ok: bool) -> None:

        was_online = self._nano_online
        self._nano_online = ok

        header_matches = self.query(AppHeader)
        header = header_matches.first() if header_matches else None

        if ok:
            self._nano_check_interval = self.NANO_CHECK_MIN_INTERVAL

            if header:
                header.set_disconnected_banner(False)

            if was_online is False:
                # Recovered from an outage - refresh everything right
                # away instead of waiting for each screen's own timer.
                self.notify("Nano connection restored", severity="information")
                self.refresh_all_screens()

        else:
            if was_online is True:
                self.notify("Lost connection to Nano", severity="warning")

            # Persistent banner, not a toast - stays up for the whole
            # outage instead of fading after a few seconds while still
            # disconnected.
            if header:
                header.set_disconnected_banner(True)

            # Back off so a genuinely offline Nano isn't hammered with
            # checks forever.
            self._nano_check_interval = min(
                self._nano_check_interval * 2, self.NANO_CHECK_MAX_INTERVAL
            )

        self._schedule_next_nano_check()


if __name__ == "__main__":

    NanoDashboard().run()
