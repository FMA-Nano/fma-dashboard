from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Static, Button, Label
from textual.binding import Binding

from widgets.status_card import StatusCard
from services import cronjobs as cron_service

class CronJobPage(VerticalScroll):


    def compose(self):

        yield Static(
            "[bold]Cron Jobs[/bold]",
            classes="page-title"
        )


        # ------------------------
        # ------ Cronjobs --------
        # ------------------------ 
        # yield Static("[bold]Cron Jobs[/bold]", classes="page-title")

        user_jobs = cron_service.get_user_cron()
        root_jobs = cron_service.get_root_cron()

        self.user_card = StatusCard(
            "User Cron Jobs",
            [
                (f"Job {i+1}", job)
                for i, job in enumerate(user_jobs)
            ]
        )
        yield self.user_card

        self.root_card = StatusCard(
            "Root Cron Jobs",
            [
                (f"Job {i+1}", job)
                for i, job in enumerate(root_jobs)
            ]
        )
        yield self.root_card

    def on_mount(self) -> None:
        # Re-run refresh_data() every REFRESH_SECONDS while this page exists.
        self.set_interval(60, self.refresh_data)


    def refresh_data(self):

        # ------------------------
        # -- Refresh Cronjobs ----
        # ------------------------ 
        user_jobs = cron_service.get_user_cron()
        root_jobs = cron_service.get_root_cron()

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
        