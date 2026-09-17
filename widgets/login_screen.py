from textual.screen import ModalScreen
from textual.widgets import Static, Button, Label, Input, Select
from textual.containers import Vertical, Horizontal
from textual import work

from services import config as nano_config
from services import local_info
from services.remote import warm_connection, close_connection


class LoginScreen(ModalScreen):
    """Gathers host/port/user/password, verifies the connection works,
    saves it, then dismisses itself.

    Used in two situations:
    - On a fresh machine at startup (no saved connection yet) - nothing
      is mounted underneath, so this is effectively the whole screen.
    - After the user clicks "Disconnect" in the header while the
      dashboard is already running - being a ModalScreen, this overlays
      on top of (and blocks interaction with) the existing UI until
      dismissed, so no stale data from the old Nano is visible/usable
      while switching.

    Dismisses with True if a connection was actually made, False if the
    user chose Skip - callers can use this to decide whether a refresh
    is worthwhile, though in practice both cases warrant one (Skip after
    a Disconnect should still clear stale data from view).
    """

    DEFAULT_CSS = """
    LoginScreen {
        align: center middle;
        background: #0b1f33;
    }

    #login_box {
        width: 60;
        height: auto;
        background: #10131a;
        border: round #2b3542;
        padding: 2 4;
    }

    #login_title {
        width: 100%;
        content-align: center middle;
        color: #00a8ff;
        text-style: bold;
        margin-bottom: 1;
    }

    #login_subtitle {
        width: 100%;
        content-align: center middle;
        color: #9aa5b1;
        margin-bottom: 2;
    }

    .login-row {
        height: auto;
        margin-bottom: 1;
        align: left middle;
    }

    .login-row Label {
        width: 12;
        color: #b7c0cc;
    }

    .login-control {
        width: 1fr;
    }

    #login_status {
        width: 100%;
        content-align: center middle;
        margin-top: 1;
        margin-bottom: 1;
        color: #9aa5b1;
    }

    #login_actions {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    #login_actions Button {
        margin: 0 1;
        min-width: 12;
    }

    #connect_login {
        background: #2f6fa3;
        color: white;
    }

    #skip_login {
        background: transparent;
        border: solid #2b3542;
        color: #9aa5b1;
    }

    #quit_login {
        background: transparent;
        border: solid #6b2b2b;
        color: #c98a8a;
    }

    #local_connect_row {
        width: 100%;
        align: center middle;
        margin-bottom: 2;
    }

    #connect_local_button {
        background: #3a6e4a;
        color: white;
        width: 100%;
    }

    #local_status {
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
        color: #9aa5b1;
    }

    .login-divider {
        width: 100%;
        content-align: center middle;
        color: #4b5563;
        margin-bottom: 1;
    }
    """

    def compose(self):

        current = nano_config.get_nano()
        sites = nano_config.list_sites()
        is_nano = local_info.is_running_on_nano()

        with Vertical(id="login_box"):

            yield Static("FMA DEVICE MANAGEMENT CONSOLE", id="login_title")
            yield Static("Connect to a NanoPC to continue", id="login_subtitle")

            with Vertical(id="local_connect_row"):
                label = "Connect to This Nano" if is_nano else "Connect to This Device"
                yield Button(label, id="connect_local_button")

            self.local_status = Static("", id="local_status")
            yield self.local_status

            yield Static("— or enter connection details manually —", classes="login-divider")

            if sites:
                with Horizontal(classes="login-row"):
                    yield Label("Saved Site")
                    yield Select(
                        [(site["name"], site["name"]) for site in sites],
                        prompt="Choose a saved site...",
                        id="login_site_select",
                        classes="login-control",
                    )

            with Horizontal(classes="login-row"):
                yield Label("Host")
                yield Input(
                    value=current["host"],
                    placeholder="e.g. remote.fmafrica.com",
                    id="login_host",
                    classes="login-control",
                )

            with Horizontal(classes="login-row"):
                yield Label("Port")
                yield Input(
                    value=str(current.get("port", 22)),
                    placeholder="22",
                    id="login_port",
                    classes="login-control",
                )

            with Horizontal(classes="login-row"):
                yield Label("User")
                yield Input(
                    value=current["user"],
                    placeholder="pi",
                    id="login_user",
                    classes="login-control",
                )

            with Horizontal(classes="login-row"):
                yield Label("Password")
                yield Input(
                    value=current["password"],
                    password=True,
                    id="login_password",
                    classes="login-control",
                )

            self.login_status = Static("", id="login_status")
            yield self.login_status

            with Horizontal(id="login_actions"):
                yield Button("Connect", id="connect_login")
                yield Button("Skip", id="skip_login")
                yield Button("Quit", id="quit_login")

    def on_mount(self):
        self.query_one("#login_host", Input).focus()

    def on_select_changed(self, event: Select.Changed):
        if event.select.id != "login_site_select":
            return

        # Avoid depending on Select.BLANK - its exact behavior/location
        # has varied across Textual versions. get_site() already returns
        # None for anything that isn't a real saved site name (including
        # whatever the "nothing selected" placeholder value happens to
        # be), so checking that alone is enough and version-agnostic.
        site = nano_config.get_site(event.value)
        if not site:
            return

        self.query_one("#login_host", Input).value = site["host"]
        self.query_one("#login_port", Input).value = str(site.get("port", 22))
        self.query_one("#login_user", Input).value = site["user"]
        self.query_one("#login_password", Input).value = site["password"]

    def on_button_pressed(self, event):

        if event.button.id == "connect_login":
            self.connect()

        elif event.button.id == "skip_login":
            self.dismiss(False)

        elif event.button.id == "connect_local_button":
            self.connect_local()

        elif event.button.id == "quit_login":
            self.app.exit()

    def on_input_submitted(self, event: Input.Submitted):
        # Pressing Enter in any field also tries to connect, so the
        # keyboard-only path is: type, Tab, type, Tab, ..., Enter.
        self.connect()

    def connect(self):

        host = self.query_one("#login_host", Input).value.strip()
        port_text = self.query_one("#login_port", Input).value.strip()
        user = self.query_one("#login_user", Input).value.strip() or "pi"
        password = self.query_one("#login_password", Input).value

        if not host:
            self.login_status.update("[#E05C5C]Host is required[/#E05C5C]")
            return

        if not password:
            self.login_status.update("[#E05C5C]Password is required[/#E05C5C]")
            return

        if port_text and not port_text.isdigit():
            self.login_status.update("[#E05C5C]Port must be a number[/#E05C5C]")
            return

        port = int(port_text) if port_text else 22

        self.query_one("#connect_login", Button).disabled = True
        self.login_status.update(f"Connecting to {user}@{host}:{port}...")
        self._connect_worker(host, port, user, password)

    @work(thread=True, exclusive=True, group="login-connect")
    def _connect_worker(self, host, port, user, password):

        try:
            close_connection()
        except Exception:
            pass

        nano_config.set_nano(host=host, port=port, user=user, password=password)

        result = warm_connection(timeout=10)

        if result.ok:
            nano_config.save_nano()

        self.app.call_from_thread(self._apply_result, host, port, user, result)

    def _apply_result(self, host, port, user, result):

        self.query_one("#connect_login", Button).disabled = False

        if result.ok:
            self.login_status.update(
                f"[#5FD68A]Connected to {user}@{host}:{port}[/#5FD68A]"
            )
            self.dismiss(True)
        else:
            self.login_status.update(
                f"[#E05C5C]Could not connect: {result.status_word()}[/#E05C5C]"
            )

    # ------------------------------------------------------------------
    # "Connect to This Device" - for when the dashboard is running
    # directly on a Nano and wants to point itself at itself, without
    # the person having to know/type its own IP.
    # ------------------------------------------------------------------

    def connect_local(self):

        user = self.query_one("#login_user", Input).value.strip() or "pi"
        password = self.query_one("#login_password", Input).value or "pi"

        self.query_one("#connect_local_button", Button).disabled = True
        self.local_status.update("Scanning local addresses...")
        self._connect_local_worker(user, password)

    @work(thread=True, exclusive=True, group="login-connect-local")
    def _connect_local_worker(self, user, password):

        candidates = local_info.get_local_candidate_hosts()
        found_host = None

        for candidate in candidates:
            nano_config.set_nano(host=candidate, port=22, user=user, password=password, name="_local_scan")
            result = warm_connection(nano="_local_scan", timeout=3)

            self.app.call_from_thread(
                self.local_status.update, f"Trying {candidate}..."
            )

            if result.ok:
                found_host = candidate
                break

        if found_host:
            try:
                close_connection()
            except Exception:
                pass

            nano_config.set_nano(host=found_host, port=22, user=user, password=password)
            nano_config.save_nano()

            self.app.call_from_thread(self._apply_local_result, found_host, user, True, candidates)
        else:
            self.app.call_from_thread(self._apply_local_result, None, user, False, candidates)

    def _apply_local_result(self, found_host, user, success, tried):

        self.query_one("#connect_local_button", Button).disabled = False

        if success:
            self.local_status.update(
                f"[#5FD68A]Connected to {user}@{found_host} (local)[/#5FD68A]"
            )
            self.dismiss(True)
        else:
            tried_text = ", ".join(tried)
            self.local_status.update(
                f"[#E05C5C]Could not connect on any local address ({tried_text}). "
                f"Check sshd is running and the password is correct.[/#E05C5C]"
            )
