from textual.screen import Screen
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static, Button, Select, Input, Label
from textual import work

from services import log_files as log_files_service


class LogViewerScreen(Screen):
    """Full-screen log viewer for one folder (e.g. "Pumps") - pick a
    day/file from the dropdown, set how many lines to show, view the
    content in a large scrollable area.

    Pushed via push_screen() rather than embedded in the sidebar's
    ContentSwitcher, so it genuinely takes over the whole terminal (no
    sidebar/header sharing space with it) - this is what "full screen"
    actually means here.

    Content is always mounted as a brand new Static rather than reusing
    one long-lived widget and calling .update() on it repeatedly - a
    freshly mounted widget always gets its height correctly measured
    from scratch, which is what makes the scroll area actually reflect
    the full content instead of getting stuck at whatever height an
    earlier, much shorter render happened to settle on.
    """

    BINDINGS = [("escape", "go_back", "Back")]

    DEFAULT_CSS = """
    LogViewerScreen {
        background: $surface;
    }

    #log_viewer_topbar {
        height: auto;
        align: left middle;
        margin: 1 2;
    }

    #log_viewer_topbar Button {
        margin-right: 2;
    }

    #log_viewer_controls {
        height: auto;
        align: left middle;
        margin: 0 2 1 2;
    }

    #log_viewer_controls Label {
        margin-right: 1;
        color: #b7c0cc;
    }

    #log_viewer_controls Select {
        width: 40;
        margin-right: 2;
    }

    #log_viewer_controls Input {
        width: 14;
        margin-right: 1;
    }

    #log_viewer_status {
        margin: 0 2 1 2;
        color: #9aa5b1;
    }

    #log_viewer_scroll {
        height: 1fr;
        margin: 0 2 1 2;
        border: round #2b3542;
        padding: 1 2;
    }

    .log-content-text {
        color: #d8dee9;
    }
    """

    def __init__(self, folder: str):
        super().__init__()
        self.folder = folder
        self.current_file = None

    def compose(self):

        with Horizontal(id="log_viewer_topbar"):
            yield Button("< Back", id="log_viewer_back")
            yield Static(f"[bold]{self.folder}[/bold]", classes="page-title")

        with Horizontal(id="log_viewer_controls"):
            yield Label("Day / File:")
            self.file_select = Select([], id="log_file_select", allow_blank=True)
            yield self.file_select
            yield Label("Lines:")
            self.lines_input = Input(value="500", id="log_viewer_lines_input")
            yield self.lines_input
            yield Button("Load", id="log_viewer_load")
            yield Button("All", id="log_viewer_all")

        self.status = Static("Loading file list...", id="log_viewer_status")
        yield self.status

        self.scroll_area = VerticalScroll(id="log_viewer_scroll")
        yield self.scroll_area

    def on_mount(self) -> None:
        self._fetch_file_list()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    # ------------------------------------------------------------------
    # File list (populates the Day/File dropdown)
    # ------------------------------------------------------------------

    @work(thread=True, exclusive=True, group="log-viewer")
    def _fetch_file_list(self) -> None:
        files = log_files_service.list_log_files(self.folder)
        self.app.call_from_thread(self._apply_file_list, files)

    def _apply_file_list(self, files) -> None:

        if files is None:
            self.status.update("[#E05C5C]Could not reach the Nano.[/#E05C5C]")
            return

        if not files:
            self.status.update("No files found in this folder.")
            return

        options = [(f"{f['name']}   ({f['modified']})", f["name"]) for f in files]
        self.file_select.set_options(options)

        # Auto-select the most recent file (today's log) and load it
        # immediately, rather than making the person pick before seeing
        # anything.
        first_name = files[0]["name"]
        self.file_select.value = first_name
        self.current_file = first_name
        self._load_content(self.lines_input.value)

    def on_select_changed(self, event) -> None:
        # Avoid depending on Select.BLANK (version-sensitive across
        # Textual releases) - file names are always non-empty strings,
        # so a truthy check is enough and works regardless of version.
        if event.select is self.file_select and event.value:
            self.current_file = event.value
            self._load_content(self.lines_input.value)

    # ------------------------------------------------------------------
    # Content loading
    # ------------------------------------------------------------------

    def on_button_pressed(self, event) -> None:

        if event.button.id == "log_viewer_back":
            self.app.pop_screen()

        elif event.button.id == "log_viewer_load":
            self._load_content(self.lines_input.value)

        elif event.button.id == "log_viewer_all":
            self.lines_input.value = "all"
            self._load_content("all")

    def on_input_submitted(self, event) -> None:
        if event.input is self.lines_input:
            self._load_content(self.lines_input.value)

    @staticmethod
    def _parse_lines_setting(raw):
        """Returns an int line count, or None meaning "no limit / all"."""
        raw = (raw or "").strip().lower()
        if raw in ("", "all"):
            return None
        try:
            value = int(raw)
            return value if value > 0 else None
        except ValueError:
            return None

    def _load_content(self, lines_setting) -> None:
        if not self.current_file:
            return
        self.status.update(f"Loading {self.current_file}...")
        self._fetch_content(self.folder, self.current_file, lines_setting)

    @work(thread=True, exclusive=True, group="log-viewer")
    def _fetch_content(self, folder, filename, lines_setting) -> None:
        tail_lines = self._parse_lines_setting(lines_setting)
        content = log_files_service.read_log_file(folder, filename, tail_lines=tail_lines)
        self.app.call_from_thread(self._apply_content, folder, filename, content)

    def _apply_content(self, folder, filename, content) -> None:

        if folder != self.folder or filename != self.current_file:
            return  # user picked a different file before this finished

        self.scroll_area.remove_children()

        if content is None:
            self.status.update("[#E05C5C]Could not read this file.[/#E05C5C]")
            return

        if not content.strip():
            self.status.update("(empty file)")
            return

        line_count = content.count("\n") + 1
        self.status.update(f"{filename} - {line_count} line(s)")
        self.scroll_area.mount(Static(content, classes="log-content-text"))
