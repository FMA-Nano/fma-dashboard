from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Static, Button, Label
from textual.binding import Binding

from services import settings as settings_service


class SettingsPage(VerticalScroll):

    BINDINGS = [
        Binding("up", "previous_row", "Up"),
        Binding("down", "next_row", "Down"),
        Binding("left", "previous_value", "Left"),
        Binding("right", "next_value", "Right"),
        Binding("enter", "select", "Select"),
        Binding("space", "select", "Select"),
    ]


    def compose(self):

        yield Static(
            "[bold]Settings[/bold]",
            classes="page-title"
        )


        # -----------------------------
        # Refresh Rate
        # -----------------------------

        yield Label(
            "Refresh Rate",
            classes="section-title"
        )


        with Horizontal(id="refresh_buttons"):

            yield Button(
                "5s",
                id="refresh_5",
                classes="setting-button"
            )

            yield Button(
                "10s",
                id="refresh_10",
                classes="setting-button"
            )

            yield Button(
                "30s",
                id="refresh_30",
                classes="setting-button"
            )


        # -----------------------------
        # Keyboard Help
        # -----------------------------

        yield Static(
            "[bold]Keyboard Shortcuts[/bold]",
            classes="section-title"
        )


        yield Static(
            "↑ ↓      Navigate\n"
            "← →      Change Value\n"
            "SPACE    Select\n"
            "ENTER    Select\n"
            "ESC      Back\n"
            "Q        Quit",
            classes="info-block",
        )



    def on_mount(self):

        # Menu rows

        self.rows = [
            "refresh"
        ]


        self.current_row = 0


        # Buttons

        self.refresh_values = [
            "refresh_5",
            "refresh_10",
            "refresh_30",
        ]


        # Get saved setting

        current = settings_service.get_refresh_interval()


        if current == 5:
            self.refresh_index = 0

        elif current == 10:
            self.refresh_index = 1

        elif current == 30:
            self.refresh_index = 2

        else:
            self.refresh_index = 0



        # Cursor starts on saved value

        self.cursor_index = self.refresh_index


        self.update_menu()



    # --------------------------------
    # Move between settings
    # --------------------------------

    def action_next_row(self):

        if self.current_row < len(self.rows) - 1:
            self.current_row += 1

        self.update_menu()



    def action_previous_row(self):

        if self.current_row > 0:
            self.current_row -= 1

        self.update_menu()



    # --------------------------------
    # Move cursor
    # --------------------------------

    def action_next_value(self):

        if self.current_row == 0:

            if self.cursor_index < len(self.refresh_values) - 1:
                self.cursor_index += 1


        self.update_menu()



    def action_previous_value(self):

        if self.current_row == 0:

            if self.cursor_index > 0:
                self.cursor_index -= 1


        self.update_menu()



    # --------------------------------
    # Save value
    # --------------------------------

    def action_select(self):

        if self.current_row == 0:

            values = [
                5,
                10,
                30
            ]


            selected = values[self.cursor_index]


            # Save setting

            settings_service.set_refresh_interval(
                selected
            )


            # Update blue selected

            self.refresh_index = self.cursor_index


            print(
                "Refresh rate changed:",
                selected
            )


        self.update_menu()



    # --------------------------------
    # Update colours
    # --------------------------------

    def update_menu(self):

        buttons = [
            "refresh_5",
            "refresh_10",
            "refresh_30",
        ]


        # Clear colours

        for button_id in buttons:

            button = self.query_one(
                "#" + button_id
            )

            button.remove_class(
                "active-value"
            )

            button.remove_class(
                "cursor-value"
            )



        # -------------------------
        # Blue = saved setting
        # -------------------------

        active = self.refresh_values[
            self.refresh_index
        ]


        self.query_one(
            "#" + active
        ).add_class(
            "active-value"
        )



        # -------------------------
        # Green = cursor position
        # -------------------------

        cursor = self.refresh_values[
            self.cursor_index
        ]


        self.query_one(
            "#" + cursor
        ).add_class(
            "cursor-value"
        )