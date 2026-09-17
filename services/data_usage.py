"""Data usage service.

Reads from dataUsage.db on the Nano over SSH:

- daily_state.totals_json - a single row, continuously overwritten by
  the monitoring script, holding today's running totals broken down by
  application. Already aggregated on the Nano side, so this is a simple
  single-row read + JSON parse, no SUM/GROUP BY needed.

- usage_log - one row per flush interval (hourly in production),
  application-level rx/tx/total plus a JSON "detail" breakdown. Filtered
  to today's rows only, most recent first.

- file_data_usage - one row per flush interval, process-level detail
  (program/pid/user/executable/command). Same shape as usage_log, also
  filtered to today only.
"""

import json
import datetime

from services.remote import query_remote_sqlite, run_remote

DATA_USAGE_DB = "/home/pi/ST500V3/Main/dataUsage.db"

HISTORY_LIMIT = 20  # most recent rows to show for usage_log/file_data_usage


def _kb_to_mb(value):
    """The rx/tx values in daily_state.totals_json are in kilobytes
    (confirmed by cross-checking against data-usage-monitor's own
    hourly MB totals - if these were raw bytes the numbers would be
    implausibly tiny, and if they were already MB a single curl call
    would exceed the device's entire hourly usage).
    """
    try:
        return round(float(value) / 1024, 2)
    except (TypeError, ValueError):
        return 0.0


def _format_kb(value):
    """Same scaling as the monitor script's own format_kb() - dynamic
    KB/MB/GB display, since a single history row can range from a few
    KB (systemd-resolved) to several MB (an hour of curl polling).
    """
    try:
        kb = float(value)
    except (TypeError, ValueError):
        return "-"

    if kb >= 1024 * 1024:
        return f"{kb / (1024 * 1024):.2f} GB"
    if kb >= 1024:
        return f"{kb / 1024:.1f} MB"
    return f"{kb:.0f} KB"


def _today_prefix():
    """Today's date in the DD/MM/YYYY format used by the monitor
    script's own now_str(), for a LIKE-prefix match against timestamps.
    """
    return datetime.date.today().strftime("%d/%m/%Y")


def get_todays_usage():
    """Return today's data usage totals so far.

    Returns:
        {
            "date": "2026-09-08",
            "applications": [
                {"name": "curl", "rx_mb": 3.66, "tx_mb": 0.23, "total_mb": 3.89},
                ...
            ],
            "total_rx_mb": ...,
            "total_tx_mb": ...,
            "total_mb": ...,
        }

    On failure (offline, no row yet, malformed JSON), returns the same
    shape with an empty applications list and a status word in "date"
    so the UI has something sensible to show rather than crashing.
    """

    rows = query_remote_sqlite(
        DATA_USAGE_DB,
        "SELECT date, totals_json FROM daily_state WHERE id = 1 LIMIT 1",
    )

    empty = {
        "date": "-",
        "applications": [],
        "total_rx_mb": 0.0,
        "total_tx_mb": 0.0,
        "total_mb": 0.0,
    }

    if rows is None:
        empty["date"] = "Offline"
        return empty

    if not rows or not rows[0]:
        empty["date"] = "No Data Yet"
        return empty

    date, totals_json = rows[0]

    try:
        totals = json.loads(totals_json)
    except Exception:
        empty["date"] = "Parse Error"
        return empty

    applications = []
    total_rx = 0.0
    total_tx = 0.0

    for name, usage in (totals.get("applications") or {}).items():
        rx_mb = _kb_to_mb(usage.get("rx", 0))
        tx_mb = _kb_to_mb(usage.get("tx", 0))
        total_rx += rx_mb
        total_tx += tx_mb
        applications.append({
            "name": name,
            "rx_mb": rx_mb,
            "tx_mb": tx_mb,
            "total_mb": round(rx_mb + tx_mb, 2),
        })

    # Largest consumer first.
    applications.sort(key=lambda app: app["total_mb"], reverse=True)

    return {
        "date": date,
        "applications": applications,
        "total_rx_mb": round(total_rx, 2),
        "total_tx_mb": round(total_tx, 2),
        "total_mb": round(total_rx + total_tx, 2),
    }


def _fetch_history(table, limit):
    """Shared logic for usage_log and file_data_usage - both share the
    exact same (id, timestamp, rx, tx, total, detail) shape after the
    monitor script's schema update, so one query pattern covers both.

    Returns a list of {timestamp, rx, tx, total (display strings),
    detail (parsed list, or [] on parse failure)} dicts, most recent
    first - or None if the query failed outright (offline, etc), so
    callers can distinguish "genuinely no data" from "couldn't reach it".
    """

    rows = query_remote_sqlite(
        DATA_USAGE_DB,
        f"SELECT timestamp, rx, tx, total, detail FROM {table} "
        f"WHERE timestamp LIKE ? ORDER BY id DESC LIMIT ?",
        params=[f"{_today_prefix()}%", limit],
    )

    if rows is None:
        return None

    entries = []

    for timestamp, rx, tx, total, detail in rows:

        try:
            detail_list = json.loads(detail)
        except Exception:
            detail_list = []

        entries.append({
            "timestamp": timestamp,
            "rx": _format_kb(rx),
            "tx": _format_kb(tx),
            "total": _format_kb(total),
            "detail": detail_list,
        })

    return entries


def get_program_usage_today(limit=HISTORY_LIMIT):
    """Today's usage_log rows (application-level), most recent first.
    Each entry's "detail" is a list of {name, rx_kb, tx_kb, total_kb}.
    """
    return _fetch_history("usage_log", limit)


def get_file_usage_today(limit=HISTORY_LIMIT):
    """Today's file_data_usage rows (process-level), most recent first.
    Each entry's "detail" is a list of {program, pid, user, executable,
    command, rx_kb, tx_kb, total_kb}.
    """
    return _fetch_history("file_data_usage", limit)


def get_vnstat_today():
    """Today's traffic per interface, straight from vnstat's own kernel-
    level byte counters - independent of the nethogs-based, per-
    application numbers used everywhere else on this page (and likely a
    different total, since nethogs can miss traffic it can't attribute
    to a tracked process, while vnstat counts every byte regardless).

    Deliberately NOT summed across interfaces: wg1 (WireGuard) rides on
    top of whichever physical interface (eth0/wlan0) actually carries
    it, so its traffic is already counted once on that physical
    interface - adding wg1's total on top would double-count. Each
    interface's numbers are returned separately instead.

    Returns a list of {name, rx_mb, tx_mb, total_mb} dicts, or None on
    failure (vnstat not installed, offline, no data collected yet, etc).
    """

    result = run_remote(["vnstat", "--json", "d", "1"], timeout=8)

    if not result.ok:
        return None

    try:
        data = json.loads(result.stdout)
    except Exception:
        return None

    interfaces = []

    for iface in data.get("interfaces", []):

        name = iface.get("name", "?")
        days = iface.get("traffic", {}).get("day", [])

        if not days:
            continue

        # --json d 1 asks for just the most recent day, so this is
        # today's entry (assuming vnstat has already logged something
        # today, which it will have if the interface has seen any
        # traffic at all).
        today_entry = days[-1]

        rx = today_entry.get("rx", 0)
        tx = today_entry.get("tx", 0)

        interfaces.append({
            "name": name,
            "rx_mb": round(rx / (1024 * 1024), 2),
            "tx_mb": round(tx / (1024 * 1024), 2),
            "total_mb": round((rx + tx) / (1024 * 1024), 2),
        })

    return interfaces
