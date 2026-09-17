from textual.containers import VerticalScroll
from textual.widgets import Static
from textual import work

from services import ssh

REFRESH_INTERVAL = 30  # login history doesn't need to be checked as often


class SecurityPage(VerticalScroll):
    """compose() only builds a placeholder - the SSH login history fetch
    (sudo journalctl ...) happens in a background worker so this screen
    never blocks the UI thread on mount.
    """

    BINDINGS = [
        ("up", "cursor_up", "ScrollUp"),
        ("down", "cursor_down", "Scroll Down"),
    ]

    def compose(self):

        yield Static(
            "[bold]SSH Login History[/bold]",
            classes="page-title"
        )

        self.history = Static("Loading...", classes="info-block")
        yield self.history

    def on_mount(self) -> None:
        self.refresh_data()
        self.set_interval(REFRESH_INTERVAL, self.refresh_data)

    def on_show(self) -> None:
        self._fetch_data()

    def force_refresh(self) -> None:
        """Immediately re-fetch, bypassing the visibility check - used
        when the active Nano connection changes.
        """
        self._fetch_data()

    def refresh_data(self) -> None:
        if not self.display:
            return
        self._fetch_data()

    @work(thread=True, exclusive=True, group="security-page")
    def _fetch_data(self) -> None:
        logs = ssh.get_ssh_history(20)
        self.app.call_from_thread(self._apply_data, logs)

    def _apply_data(self, logs) -> None:
        self.history.update(self._render_history(logs))

    def _render_history(self, logs) -> str:

        output = ""

        # Header

        output += (
            f"{'Date':<14}"
            f"{'Time':<10}"
            f"{'Event'}\n"
        )

        output += "-" * 80 + "\n"

        for log in logs:

            description = log["description"]

            # Select icon

            if "Accepted" in description:

                icon = "  "

            elif "Failed" in description:

                icon = "⚠️ "

            elif "Disconnected" in description:

                icon = "  "

            elif "session closed" in description:

                icon = "  "

            elif "PAM" in description:
                icon = "‼️ "

            else:

                icon = "  "

            # Remove noisy ssh information

            description = (
                description
                .replace("sshd:", "")
                .replace("pam_unix(sshd:session):", "")
            )

            output += (
                f"{log['date']:<14}"
                f"{log['time']:<10}"
                f"{icon} {description}\n"
            )

        return output
