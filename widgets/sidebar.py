from textual.widgets import ListView, ListItem, Label
from textual.message import Message


class NavItem(ListItem):

    def __init__(self, key: str, label: str):

        super().__init__(Label(label))

        self.key = key


class Sidebar(ListView):
    """Fixed left-hand navigation menu."""

    BINDINGS = [

        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("enter", "select_cursor", "Open"),

    ]

    class NavSelected(Message):

        def __init__(self, key: str):

            self.key = key

            super().__init__()


    PAGES = [

        ("dashboard", "Dashboard"),
        ("pumps", "Pumps & Tanks"),
        ("network", "Network"),
        ("security", "Security"),
        ("cronjobs", "Cron Jobs"),
        # ("logs", "Logs"),
        # ("settings", "Settings"),
        ("system", "System"),
        ("about", "About"),

    ]


    def __init__(self):

        items = [
            NavItem(key, label)
            for key, label in self.PAGES
        ]

        super().__init__(
            *items,
            id="sidebar"
        )


    def on_list_view_selected(
        self,
        event: ListView.Selected
    ) -> None:

        event.stop()

        self.post_message(
            self.NavSelected(event.item.key)
        )