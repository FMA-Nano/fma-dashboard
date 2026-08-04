from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static


PLACEHOLDER_LOGS = "\n".join(
    [f"[dim]12:{m:02d}:00[/dim]  Placeholder log line {m}" for m in range(60)]
)


class LogsPage(VerticalScroll):
    def compose(self):
        yield Static("[bold]Logs[/bold]", classes="page-title")

        yield Static("[bold]Application Logs[/bold]", classes="section-title")
        with VerticalScroll(classes="log-window"):
            yield Static(PLACEHOLDER_LOGS)

        yield Static("[bold]System Logs[/bold]", classes="section-title")
        with VerticalScroll(classes="log-window"):
            yield Static(PLACEHOLDER_LOGS)

        yield Static("[bold]Error Logs[/bold]", classes="section-title")
        with VerticalScroll(classes="log-window"):
            yield Static("[red]No errors recorded (placeholder).[/red]")
