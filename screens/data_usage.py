from textual.containers import VerticalScroll
from textual.widgets import Static
from textual import work

from widgets.status_card import StatusCard
from services import data_usage as data_usage_service

REFRESH_INTERVAL = 20  # matches the cadence of other network-adjacent data


class DataUsagePage(VerticalScroll):
    """Data usage for today, in three parts:

    - Today's Usage / By Application - the running totals so far today,
      from dataUsage.db's daily_state table (a single row the Nano's
      monitoring script keeps overwriting).
    - Program Usage (Today) - usage_log history, one entry per flush
      interval, application-level.
    - File Usage (Today) - file_data_usage history, one entry per flush
      interval, process-level (program/pid/user).

    Both history sections are filtered to today's rows only and capped
    to the most recent HISTORY_LIMIT entries.
    """

    def compose(self):

        yield Static("[bold]Data Usage[/bold]", classes="page-title")

        self.summary_card = StatusCard("Today's Usage", [
            ("Date", "Loading..."),
            ("Total RX", "-"),
            ("Total TX", "-"),
            ("Total", "-"),
        ])
        yield self.summary_card

        self.apps_card = StatusCard("By Application", [
            ("Loading...", ""),
        ])
        yield self.apps_card

        self.vnstat_card = StatusCard("Interface Totals (vnstat)", [
            ("Loading...", ""),
        ])
        yield self.vnstat_card

        yield Static("[bold]Program Usage (Today)[/bold]", classes="page-title")
        self.program_history = Static("Loading...", classes="info-block")
        yield self.program_history

        yield Static("[bold]File Usage (Today)[/bold]", classes="page-title")
        self.file_history = Static("Loading...", classes="info-block")
        yield self.file_history

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

    def refresh_data(self) -> None:
        if not self.display:
            return
        self._fetch_data()

    @work(thread=True, exclusive=True, group="data-usage-page")
    def _fetch_data(self) -> None:
        usage = data_usage_service.get_todays_usage()
        program_history = data_usage_service.get_program_usage_today()
        file_history = data_usage_service.get_file_usage_today()
        vnstat = data_usage_service.get_vnstat_today()
        self.app.call_from_thread(self._apply_data, usage, program_history, file_history, vnstat)

    def _apply_data(self, usage, program_history, file_history, vnstat) -> None:

        self.summary_card.update_rows([
            ("Date", usage["date"]),
            ("Total RX", f"{usage['total_rx_mb']} MB"),
            ("Total TX", f"{usage['total_tx_mb']} MB"),
            ("Total", f"{usage['total_mb']} MB"),
        ])

        if usage["applications"]:
            rows = []
            for app in usage["applications"]:
                rx_str = f"{app['rx_mb']} MB".rjust(9)
                tx_str = f"{app['tx_mb']} MB".rjust(9)
                total_str = f"{app['total_mb']} MB".rjust(10)
                rows.append((app["name"], f"RX {rx_str} | TX {tx_str} | Total {total_str}"))
        else:
            rows = [("No data yet today", "")]

        self.apps_card.update_rows(rows)

        if vnstat is None:
            vnstat_rows = [("Could not reach vnstat", "")]
        elif not vnstat:
            vnstat_rows = [("No interfaces tracked", "")]
        else:
            vnstat_rows = []
            for iface in vnstat:
                rx_str = f"{iface['rx_mb']} MB".rjust(9)
                tx_str = f"{iface['tx_mb']} MB".rjust(9)
                total_str = f"{iface['total_mb']} MB".rjust(10)
                vnstat_rows.append((iface["name"], f"RX {rx_str} | TX {tx_str} | Total {total_str}"))

        self.vnstat_card.update_rows(vnstat_rows)

        self.program_history.update(self._render_program_history(program_history))
        self.file_history.update(self._render_file_history(file_history))

    def _render_program_history(self, entries) -> str:

        if entries is None:
            return "[#E05C5C]Could not reach the Nano.[/#E05C5C]"

        if not entries:
            return "No entries yet today."

        blocks = []

        for entry in entries:

            label_width = 20

            # Header has no leading indent (indent=0), but detail rows
            # below it do (default indent=5) - widen the header's label
            # column by that same amount so the "|" columns still line
            # up exactly despite the different starting position.
            header = self._table_row_raw(
                entry["timestamp"], entry["rx"], entry["tx"], entry["total"],
                label_width + 5, indent=0,
            )
            header = f"[#4fa8e0]{header}[/#4fa8e0]"

            if isinstance(entry["detail"], list) and entry["detail"]:
                detail_lines = [
                    self._table_row(item.get("name", "?"), item, label_width)
                    for item in entry["detail"]
                ]
            elif isinstance(entry["detail"], dict) and entry["detail"].get("event"):
                # Marker rows (Rebooted, No activity, Debug Started/Ended)
                # store detail as a single {"event": ...} object, not a
                # list of program entries - show the event itself rather
                # than trying to render it as a usage breakdown.
                detail_lines = [f"     {entry['detail']['event']}"]
            else:
                detail_lines = ["     -"]

            blocks.append(header + "\n" + "\n".join(detail_lines))

        return "\n\n".join(blocks)

    def _render_file_history(self, entries) -> str:

        if entries is None:
            return "[#E05C5C]Could not reach the Nano.[/#E05C5C]"

        if not entries:
            return "No entries yet today."

        blocks = []

        for entry in entries:

            label_width = 35

            header = self._table_row_raw(
                entry["timestamp"], entry["rx"], entry["tx"], entry["total"],
                label_width + 5, indent=0,
            )
            header = f"[#4fa8e0]{header}[/#4fa8e0]"

            if isinstance(entry["detail"], list) and entry["detail"]:
                # Show the actual command where we have one (e.g. "ssh -fN
                # -R 18108:localhost:22", "python microKernel.pyc") since
                # that's far more useful than the bare program name - it's
                # what get_process_command() already captured, including
                # the "Process exited" placeholder for processes that had
                # already ended by the time we looked. Long commands (full
                # curl invocations) are truncated so the table stays
                # aligned rather than one row blowing out the width.
                detail_lines = [
                    self._table_row(
                        item.get("command") or item.get("program", "?"),
                        item,
                        label_width,
                    )
                    for item in entry["detail"]
                ]
            elif isinstance(entry["detail"], dict) and entry["detail"].get("event"):
                detail_lines = [f"     {entry['detail']['event']}"]
            else:
                detail_lines = ["     -"]

            blocks.append(header + "\n" + "\n".join(detail_lines))

        return "\n\n".join(blocks)

    @staticmethod
    def _format_kb_value(value) -> str:
        try:
            kb = float(value)
        except (TypeError, ValueError):
            return "-"

        if kb >= 1024:
            return f"{kb / 1024:.2f} MB"
        return f"{kb:.1f} KB"

    @staticmethod
    def _truncate(text, max_len) -> str:
        text = str(text)
        if len(text) <= max_len:
            return text
        return text[:max_len - 3] + "..."

    def _table_row_raw(self, label, rx_str, tx_str, total_str, label_width, indent=5) -> str:
        """One aligned row built from already-formatted RX/TX/Total
        strings (e.g. "65 KB", "1.5 MB") - used for header rows, which
        get their values pre-formatted from the service rather than raw
        KB floats. Shares the exact same column widths as _table_row()
        below so header and detail rows always line up.
        """

        label_display = self._truncate(label, label_width).ljust(label_width)
        rx_display = rx_str.rjust(9)
        tx_display = tx_str.rjust(9)
        total_display = total_str.rjust(10)

        return (
            f"{' ' * indent}{label_display} | RX {rx_display} | TX {tx_display} | "
            f"Total {total_display}"
        )

    def _table_row(self, label, item, label_width, indent=5) -> str:
        """One aligned row: "label | RX ... | TX ... | Total ..." - a
        shared builder so program-usage and file-usage tables use the
        exact same column formatting. Computes formatted values from a
        raw {rx_kb, tx_kb, total_kb} item, then delegates to
        _table_row_raw() for the actual layout.
        """

        return self._table_row_raw(
            label,
            self._format_kb_value(item.get("rx_kb", 0)),
            self._format_kb_value(item.get("tx_kb", 0)),
            self._format_kb_value(item.get("total_kb", 0)),
            label_width,
            indent,
        )
