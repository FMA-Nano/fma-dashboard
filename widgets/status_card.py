from __future__ import annotations

from textual.widgets import Static
from textual.containers import Vertical


STATUS_COLORS = {

    "ok": "#5FD68A",
    "healthy": "#5FD68A",
    "connected": "#5FD68A",
    "enabled": "#5FD68A",
    "running": "#5FD68A",
    "warning": "#E0C341",
    "degraded": "#E0C341",
    "starting": "#E0C341",
    "stopping": "#E0C341",
    "error": "#E05C5C",
    "failed": "#E05C5C",
    "disabled": "#E05C5C",
    "stopped": "#E05C5C",
    "masked": "#E05C5C",
    "not found": "#E05C5C",
    "unknown": "#9AA5B1",
}


def status_markup(value: str) -> str:
    color = STATUS_COLORS.get(value.strip().lower(), "#9AA5B1")
    return f"[{color}]{value}[/{color}]"


    

class StatusCard(Vertical):

    def __init__(
        self,
        title: str,
        rows: list[tuple[str, str]] | None = None,
        sections: list[tuple[str, list[tuple[str, str]]]] | None = None,
        id: str | None = None
    ):

        super().__init__(id=id, classes="status-card")

        self.title = title
        self.rows = rows or []
        self.sections = sections or []

        self.content = Static(
            self._render(),
            classes="status-card-body"
        )


    def compose(self):
        yield self.content


    def _render(self):

        lines = [
            f"[bold]{self.title}[/bold]",
            ""
        ]


        if self.rows:

            for label, value in self.rows:
                lines.append(
                    f"{label:<14} {status_markup(value)}"
                )


        for name, rows in self.sections:

            lines.append("")
            lines.append(
                f"[bold]{name}[/bold]"
            )

            for label, value in rows:
                lines.append(
                    f"{label:<14} {status_markup(value)}"
                )


        return "\n".join(lines)


    def update_rows(self, rows):

        self.rows = rows

        self.content.update(
            self._render()
        )