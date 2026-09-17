from __future__ import annotations

import re

from textual.widgets import Static
from textual.containers import Vertical


STATUS_COLORS = {

    "ok": "#5FD68A",
    "healthy": "#5FD68A",
    "connected": "#5FD68A",
    "enabled": "#5FD68A",
    "running": "#5FD68A",
    "active": "#5FD68A",
    "static": "#5FD68A",
    "external": "#5FD68A",
    "charging": "#5FD68A",
    "on": "#5FD68A",
    "yes": "#5FD68A",
    "warning": "#E0C341",
    "degraded": "#E0C341",
    "starting": "#E0C341",
    "stopping": "#E0C341",
    "battery": "#E0C341",
    "error": "#E05C5C",
    "failed": "#E05C5C",
    "disabled": "#E05C5C",
    "stopped": "#E05C5C",
    "masked": "#E05C5C",
    "not found": "#E05C5C",
    "not inserted": "#E05C5C",
    "not connected": "#E05C5C",
    "disconnected": "#E05C5C",
    "no": "#E05C5C",
    "unknown": "#9AA5B1",
}


def status_markup(value: str) -> str:
    color = STATUS_COLORS.get(value.strip().lower(), "#9AA5B1")
    return f"[{color}]{value}[/{color}]"


# The exact set of words RemoteResult.status_word() produces throughout
# every service in this app when a remote call fails outright (offline,
# timed out, auth failure, sshpass/ssh missing, or an unrecognized
# failure). Used to detect, generically and without touching any
# individual screen's fetch code, whether a card's last refresh actually
# succeeded - if any displayed value is one of these, the data shown is
# stale/unreachable rather than a fresh successful read.
_FAILURE_MARKERS = {"Offline", "Timeout", "Auth Error", "SSH Unavailable", "Unknown"}


def _contains_failure(rows, sections=()):
    if any(str(value).strip() in _FAILURE_MARKERS for _, value in rows):
        return True
    for _, section_rows in sections:
        if any(str(value).strip() in _FAILURE_MARKERS for _, value in section_rows):
            return True
    return False


def _visible_length(text: str) -> int:
    """Length of a label once Rich markup tags (e.g. "[bold]...[/bold]")
    are stripped out - used for column-width calculations so a markup
    heading embedded as a row label doesn't inflate the padding for
    every other row in the same card.
    """
    return len(re.sub(r"\[/?[^\]]*\]", "", text))


    

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

        # Assume fine until we know otherwise - the very first render
        # uses placeholder values ("Loading...", "-") which never match
        # a failure marker, so this naturally starts green and only
        # turns red once a real failed fetch actually comes back.
        self.last_update_ok = True

        self.content = Static(
            self._render_text(),
            classes="status-card-body"
        )


    def compose(self):
        yield self.content


    def _render_text(self):

        dot_color = "#5FD68A" if self.last_update_ok else "#E05C5C"

        lines = [
            f"[bold]{self.title}[/bold]  [{dot_color}]\u25cf[/{dot_color}]",
            ""
        ]

        # Size the label column to whatever the longest label in THIS
        # card actually is (measured by visible length, ignoring markup
        # tags), rather than a fixed guess - so values always line up
        # regardless of how long any particular label is (e.g.
        # "Router Modem Timer" vs "WireGuard"), and short-label cards
        # don't waste extra space they don't need.
        all_labels = [label for label, _ in self.rows]
        for _, rows in self.sections:
            all_labels += [label for label, _ in rows]

        label_width = max((_visible_length(label) for label in all_labels), default=14)
        label_width = max(label_width, 14)  # never narrower than before

        def pad_label(label):
            # Python's :<N padding counts raw characters, but markup
            # tags in a label (e.g. "[bold]WiFi[/bold]") aren't visible
            # once rendered - pad based on visible length instead so the
            # actual printed column still lines up.
            visible = _visible_length(label)
            return label + " " * max(label_width - visible, 0)

        if self.rows:

            for label, value in self.rows:
                lines.append(
                    f"{pad_label(label)} {status_markup(value)}"
                )


        for name, rows in self.sections:

            lines.append("")
            lines.append(
                f"[bold]{name}[/bold]"
            )

            for label, value in rows:
                lines.append(
                    f"{pad_label(label)} {status_markup(value)}"
                )


        return "\n".join(lines)


    def update_rows(self, rows):

        self.rows = rows
        self.last_update_ok = not _contains_failure(rows, self.sections)

        self.content.update(
            self._render_text()
        )