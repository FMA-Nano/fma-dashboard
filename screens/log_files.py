from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.widgets import Static, Button
from textual import work

from services import log_files as log_files_service
from screens.log_viewer_screen import LogViewerScreen

FOLDER_COLUMNS = 4


class LogFilesPage(VerticalScroll):
    """Pick a log folder (Pumps, Tanks, etc) - selecting one pushes the
    full-screen LogViewerScreen for that folder, rather than navigating
    within this embedded page, so viewing actual log content gets the
    whole terminal rather than sharing space with the sidebar/header.
    """

    def compose(self):

        yield Static("[bold]Log Files[/bold]", classes="page-title")

        self.body = Vertical()
        yield self.body

    def on_mount(self) -> None:
        self.show_folders()

    def on_show(self) -> None:
        self.show_folders()

    def force_refresh(self) -> None:
        self.show_folders()

    def show_folders(self) -> None:
        self.body.remove_children()
        self.body.mount(Static("Loading folders..."))
        self._fetch_folders()

    @work(thread=True, exclusive=True, group="log-files")
    def _fetch_folders(self) -> None:
        folders = log_files_service.list_log_folders()
        self.app.call_from_thread(self._apply_folders, folders)

    def _apply_folders(self, folders) -> None:

        self.body.remove_children()

        if folders is None:
            self.body.mount(Static("[#E05C5C]Could not reach the Nano.[/#E05C5C]"))
            return

        if not folders:
            self.body.mount(Static("No log folders found."))
            return

        for i in range(0, len(folders), FOLDER_COLUMNS):
            row = Horizontal(classes="log-folder-row")
            self.body.mount(row)
            for name in folders[i:i + FOLDER_COLUMNS]:
                btn = Button(name, classes="log-nav-button")
                btn.folder_name = name
                row.mount(btn)

    def on_button_pressed(self, event) -> None:
        button = event.button
        if hasattr(button, "folder_name"):
            self.app.push_screen(LogViewerScreen(button.folder_name))
