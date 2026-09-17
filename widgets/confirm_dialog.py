from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal


class ConfirmDialog(ModalScreen):
    """Generic confirm/cancel modal. Dismisses with True if confirmed,
    False if cancelled.

    Usage:
        def handle_result(confirmed: bool):
            if confirmed:
                ...do the thing...

        self.app.push_screen(
            ConfirmDialog("Apply changes to 3 pump(s) on the Nano?"),
            handle_result,
        )
    """

    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
        background: rgba(0, 0, 0, 0.6);
    }

    #confirm_box {
        width: 56;
        height: auto;
        background: #10131a;
        border: round #2b3542;
        padding: 2 4;
    }

    #confirm_title {
        width: 100%;
        content-align: center middle;
        color: #E0C341;
        text-style: bold;
        margin-bottom: 1;
    }

    #confirm_message {
        width: 100%;
        content-align: center middle;
        margin-bottom: 2;
    }

    #confirm_actions {
        width: 100%;
        height: auto;
        align: center middle;
    }

    #confirm_actions Button {
        margin: 0 1;
        min-width: 12;
    }

    #confirm_yes {
        background: #2f6fa3;
        color: white;
    }

    #confirm_no {
        background: transparent;
        border: solid #2b3542;
        color: #9aa5b1;
    }
    """

    def __init__(self, message: str, title: str = "Confirm", confirm_label: str = "Confirm"):
        super().__init__()
        self.message = message
        self.title_text = title
        self.confirm_label = confirm_label

    def compose(self):
        with Vertical(id="confirm_box"):
            yield Static(self.title_text, id="confirm_title")
            yield Static(self.message, id="confirm_message")
            with Horizontal(id="confirm_actions"):
                yield Button(self.confirm_label, id="confirm_yes")
                yield Button("Cancel", id="confirm_no")

    def on_button_pressed(self, event):
        if event.button.id == "confirm_yes":
            self.dismiss(True)
        else:
            self.dismiss(False)
