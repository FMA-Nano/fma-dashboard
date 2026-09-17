from textual.containers import VerticalScroll
from textual.widgets import Static
from textual import work

from widgets.status_card import StatusCard
from services import cronjobs as cron_service

REFRESH_INTERVAL = 60


class CronJobPage(VerticalScroll):
    """compose() only builds empty placeholder cards - the crontab SSH
    fetches happen in a background worker so this screen never blocks the
    UI thread on mount.
    """

    def compose(self):

        yield Static(
            "[bold]Cron Jobs[/bold]",
            classes="page-title"
        )

        self.user_card = StatusCard("User Cron Jobs", [])
        yield self.user_card

        self.root_card = StatusCard("Root Cron Jobs", [])
        yield self.root_card

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

    def refresh_data(self):
        if not self.display:
            return
        self._fetch_data()

    @work(thread=True, exclusive=True, group="cronjobs-page")
    def _fetch_data(self):
        user_jobs = cron_service.get_user_cron()
        root_jobs = cron_service.get_root_cron()
        self.app.call_from_thread(self._apply_data, user_jobs, root_jobs)

    def _apply_data(self, user_jobs, root_jobs):

        self.user_card.update_rows(
            [
                (f"Job {i+1}", job)
                for i, job in enumerate(user_jobs)
            ]
        )

        self.root_card.update_rows(
            [
                (f"Job {i+1}", job)
                for i, job in enumerate(root_jobs)
            ]
        )
