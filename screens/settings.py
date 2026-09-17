from textual.containers import Container, VerticalScroll, Horizontal, Vertical
from textual.widgets import Static, Button, Label, Input
from textual import work

from services import config as nano_config
from services.remote import warm_connection, close_connection


class SettingsPage(Container):
    """View/edit the active Nano connection, and manage a list of saved
    sites for quick switching between multiple field sites.

    Laid out as two side-by-side columns, each independently scrollable:
    Nano Connection on the left, Saved Sites on the right. Keeping them
    separate means a long sites list never overlaps or pushes around the
    connection form/Connect button.

    This is the same connection info gathered on the login gate shown
    before the main UI - this page exists so it can be changed later
    (e.g. switching to a different site) without restarting the app.
    """

    def compose(self):

        yield Static(
            "[bold]Login Settings[/bold]",
            classes="page-title"
        )

        with Horizontal(id="settings_columns"):

            with VerticalScroll(id="connection_column", classes="settings-column"):

                yield Label(
                    "Nano Connection",
                    classes="section-title"
                )

                current = nano_config.get_nano()

                with Horizontal(classes="setting-inline-row"):
                    yield Label("Host")
                    yield Input(
                        value=current["host"],
                        placeholder="e.g. remote.fmafrica.com or 172.16.70.3",
                        id="nano_host",
                        classes="settings-control",
                    )

                with Horizontal(classes="setting-inline-row"):
                    yield Label("Port")
                    yield Input(
                        value=str(current.get("port", 22)),
                        placeholder="22",
                        id="nano_port",
                        classes="settings-control",
                    )

                with Horizontal(classes="setting-inline-row"):
                    yield Label("User")
                    yield Input(
                        value=current["user"],
                        placeholder="pi",
                        id="nano_user",
                        classes="settings-control",
                    )

                with Horizontal(classes="setting-inline-row"):
                    yield Label("Password")
                    yield Input(
                        value=current["password"],
                        password=True,
                        id="nano_password",
                        classes="settings-control",
                    )

                self.connection_status = Static(
                    f"Active: {current['user']}@{current['host']}:{current.get('port', 22)}",
                    classes="setting-status",
                )
                yield self.connection_status

                with Horizontal(classes="setting-actions"):
                    yield Button("Connect", id="connect_nano")

            with VerticalScroll(id="sites_column", classes="settings-column"):

                yield Label(
                    "Saved Sites",
                    classes="section-title"
                )

                with Horizontal(classes="setting-inline-row"):
                    yield Label("Site Name")
                    yield Input(
                        placeholder="e.g. Site A",
                        id="site_name",
                        classes="settings-control",
                    )
                    yield Button("Save Current as Site", id="save_site")


                with Horizontal(classes="setting-inline-row"):
                    yield Label("Site Search")
                    yield Input(
                        placeholder="Search sites...",
                        id="site_search",
                        classes="settings-control",
                    )


                self.sites_container = Vertical(id="sites_list")
                yield self.sites_container

    def on_mount(self) -> None:
        self._render_sites()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "site_search":
            self._render_sites(event.value)

    # --------------------------------
    # Nano connection
    # --------------------------------

    def force_refresh(self) -> None:
        """Re-populate the form fields and status line from the current
        connection info - used after a Disconnect/reconnect elsewhere in
        the app, so this page doesn't keep showing a stale previous
        connection if the user visits it afterwards.
        """
        current = nano_config.get_nano()
        self.query_one("#nano_host", Input).value = current["host"]
        self.query_one("#nano_port", Input).value = str(current.get("port", 22))
        self.query_one("#nano_user", Input).value = current["user"]
        self.query_one("#nano_password", Input).value = current["password"]
        self.connection_status.update(
            f"Active: {current['user']}@{current['host']}:{current.get('port', 22)}"
        )

    def on_button_pressed(self, event):

        if event.button.id == "connect_nano":
            self.connect_to_nano()

        elif event.button.id == "save_site":
            self.save_current_as_site()

        elif event.button.id and event.button.id.startswith("use_site_"):
            index = int(event.button.id[len("use_site_"):])
            self.use_site(self._site_names[index])

        elif event.button.id and event.button.id.startswith("delete_site_"):
            index = int(event.button.id[len("delete_site_"):])
            self.delete_site(self._site_names[index])

    def connect_to_nano(self):

        host = self.query_one("#nano_host", Input).value.strip()
        port_text = self.query_one("#nano_port", Input).value.strip()
        user = self.query_one("#nano_user", Input).value.strip() or "pi"
        password = self.query_one("#nano_password", Input).value

        if not host:
            self.notify("Host is required", severity="error")
            return

        if not password:
            self.notify("Password is required", severity="error")
            return

        if port_text and not port_text.isdigit():
            self.notify("Port must be a number", severity="error")
            return

        port = int(port_text) if port_text else 22

        self.connection_status.update(f"Connecting to {user}@{host}:{port}...")
        self._connect_worker(host, port, user, password)

    @work(thread=True, exclusive=True, group="settings-connect")
    def _connect_worker(self, host, port, user, password):

        # Close the previous connection's multiplexed socket first (best
        # effort - if it fails, the old socket just sits idle until its
        # own ControlPersist timeout, harmless either way).
        try:
            close_connection()
        except Exception:
            pass

        nano_config.set_nano(host=host, port=port, user=user, password=password)

        result = warm_connection(timeout=10)

        if result.ok:
            nano_config.save_nano()

        self.app.call_from_thread(self._apply_connect_result, host, port, user, result)

    def _apply_connect_result(self, host, port, user, result):

        if result.ok:
            self.connection_status.update(
                f"[#5FD68A]Connected[/#5FD68A]: {user}@{host}:{port} (saved)"
            )
            self.notify(f"Connected to {user}@{host}:{port}", severity="information")
        else:
            self.connection_status.update(
                f"[#E05C5C]Failed[/#E05C5C]: {user}@{host}:{port} - {result.status_word()}"
            )
            self.notify(
                f"Could not connect: {result.status_word()}",
                severity="error",
            )


    # --------------------------------
    # Saved sites
    # --------------------------------

    def _render_sites(self, filter_text=""):

        for child in list(self.sites_container.children):
            child.remove()

        sites = nano_config.list_sites_by_recency()

        filter_text = (filter_text or "").strip().lower()

        if filter_text:
            sites = [
                s for s in sites
                if filter_text in s.get("name", "").lower()
                or filter_text in s.get("host", "").lower()
            ]

        self._site_names = [site["name"] for site in sites]

        if not sites:
            message = "No sites match your search." if filter_text else "No saved sites yet."
            self.sites_container.mount(
                Static(message, classes="info-block")
            )
            return

        for index, site in enumerate(sites):

            row = Horizontal(classes="setting-inline-row")
            self.sites_container.mount(row)

            row.mount(Label(f"{site['name']}  ({site['user']}@{site['host']}:{site.get('port', 22)})"))
            row.mount(Button("Use", id=f"use_site_{index}"))
            row.mount(Button("Delete", id=f"delete_site_{index}"))

        # Guarantee the newest entry (rendered first, at the top) is
        # immediately visible without any scrolling - explicit rather
        # than relying on whatever scroll position Textual leaves things
        # at after mounting a batch of new widgets.
        self.query_one("#sites_column").scroll_home(animate=False)

    def save_current_as_site(self):

        name = self.query_one("#site_name", Input).value.strip()
        host = self.query_one("#nano_host", Input).value.strip()
        port_text = self.query_one("#nano_port", Input).value.strip()
        user = self.query_one("#nano_user", Input).value.strip() or "pi"
        password = self.query_one("#nano_password", Input).value

        if not name:
            self.notify("Site name is required", severity="error")
            return

        if not host:
            self.notify("Host is required", severity="error")
            return

        if port_text and not port_text.isdigit():
            self.notify("Port must be a number", severity="error")
            return

        port = int(port_text) if port_text else 22

        if nano_config.save_site(name, host, port, user, password):
            self.notify(f"Saved site '{name}'", severity="information")
            self.query_one("#site_name", Input).value = ""
            self.query_one("#site_search", Input).value = ""
            self._render_sites()
        else:
            self.notify("Could not save site", severity="error")

    def use_site(self, name):

        site = nano_config.get_site(name)

        if not site:
            self.notify(f"Site '{name}' not found", severity="error")
            return

        self.query_one("#nano_host", Input).value = site["host"]
        self.query_one("#nano_port", Input).value = str(site.get("port", 22))
        self.query_one("#nano_user", Input).value = site["user"]
        self.query_one("#nano_password", Input).value = site["password"]

        self.notify(f"Loaded '{name}' - click Connect to switch", severity="information")

    def delete_site(self, name):

        if nano_config.delete_site(name):
            self.notify(f"Deleted site '{name}'", severity="information")
            current_filter = self.query_one("#site_search", Input).value
            self._render_sites(current_filter)
        else:
            self.notify("Could not delete site", severity="error")
