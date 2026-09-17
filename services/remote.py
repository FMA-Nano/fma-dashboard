"""Central remote-execution layer.

Every service that needs information from (or wants to act on) a NanoPC
should go through this module instead of implementing its own SSH/sshpass
plumbing. This keeps exactly one place that knows how to reach a Nano.

Usage:

    from services.remote import run_remote

    result = run_remote("sudo -n ufw status")

    if result.ok:
        ...use result.stdout...
    else:
        ...use result.error_kind to decide what to show ("Offline", "Timeout", etc)...

Design notes:
- Uses `sshpass -p <password> ssh ...` from the laptop. Never `sudo sshpass`.
  If a remote command needs root on the Nano, put `sudo` inside the command
  string itself (e.g. "sudo wg show wg1") - sudo runs *on the Nano*.
- Commands are always passed to ssh as a single remote string, so pipelines
  (e.g. "journalctl -u ssh | grep ... | tail -25") work exactly like they
  did when run locally.
- Every function here catches its own failures and returns a structured
  result rather than raising, so calling services can stay simple and
  never crash the dashboard because the Nano is offline/slow/unreachable.
- Uses SSH ControlMaster/ControlPersist multiplexing: the first call to a
  given Nano pays the full connection-setup cost (TCP + key exchange +
  auth, typically 1-3s), then opens a background master connection that
  every subsequent call reuses over a local control socket. Follow-up
  calls typically drop to well under a second. Without this, EVERY call
  pays that full setup cost again, which is why tight per-call timeouts
  (3-5s) were seen clipping calls that were otherwise working fine - the
  connection setup alone was eating the whole budget.
"""

import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from typing import List, Optional, Union

from services.config import get_nano

DEFAULT_TIMEOUT = 8  # seconds, for a single remote command
CONNECT_TIMEOUT = 5  # seconds, for establishing the SSH connection itself
CONTROL_PERSIST = "10m"  # how long the shared connection stays open after last use

# Any call slower than this gets flagged as SLOW, both in the on-disk log
# and (if enabled) printed straight to the console as it happens. Override
# with the FMA_SSH_SLOW_THRESHOLD env var (seconds) if 1.5s is too
# aggressive/lax for your network.
SLOW_THRESHOLD = float(os.environ.get("FMA_SSH_SLOW_THRESHOLD", "1.5"))

# Set FMA_SSH_LOG_CONSOLE=0 to silence the live "SLOW SSH CALL" printouts
# and only write to the log file.
_LOG_TO_CONSOLE = os.environ.get("FMA_SSH_LOG_CONSOLE", "1") != "0"

# Control sockets live in a per-user tmp dir so multiple people/checkouts
# on the same laptop don't collide.
_CONTROL_DIR = os.path.join(tempfile.gettempdir(), f"fma_ssh_control_{os.getuid() if hasattr(os, 'getuid') else 'u'}")
os.makedirs(_CONTROL_DIR, exist_ok=True)


def _control_path(conn):
    # Include port so switching a Nano's port (or connecting to a
    # different site on the same host) doesn't accidentally reuse a
    # stale multiplexed connection meant for a different target.
    port = conn.get("port", 22)
    return os.path.join(_CONTROL_DIR, f"{conn['user']}@{conn['host']}:{port}.sock")


# ---------------------------------------------------------------------------
# Call timing/logging
#
# Every run_remote() call is timed and appended to a log file so you can
# answer "what took so long?" after the fact - including during normal
# dashboard use, not just the standalone test script. Calls slower than
# SLOW_THRESHOLD are also flagged (and, unless disabled, printed live).
# ---------------------------------------------------------------------------

_LOG_PATH = os.path.join(_CONTROL_DIR, "ssh_calls.log")

# Create the file up front (even before any calls happen) so `tail -f`
# doesn't error out with "No such file" while you're getting set up.
try:
    if not os.path.exists(_LOG_PATH):
        open(_LOG_PATH, "a").close()
except Exception:
    pass


def _short_command(command):
    text = command if isinstance(command, str) else " ".join(command)
    text = " ".join(text.split())  # collapse whitespace/newlines
    return text if len(text) <= 100 else text[:97] + "..."


def _log_call(conn, command, duration, result):
    slow = duration >= SLOW_THRESHOLD
    status = "OK" if result.ok else (result.error_kind or "error")
    line = (
        f"{datetime.now().isoformat(timespec='seconds')} "
        f"{'SLOW' if slow else 'ok  '} "
        f"{duration:6.2f}s "
        f"{conn['user']}@{conn['host']} "
        f"[{status}] "
        f"{_short_command(command)}"
    )

    try:
        with open(_LOG_PATH, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass  # logging must never break a real call

    if slow and _LOG_TO_CONSOLE:
        print(f"[fma_ssh] SLOW ({duration:.2f}s): {_short_command(command)}", file=sys.stderr)


def recent_slow_calls(limit=20):
    """Return the last `limit` lines from the SSH call log that were
    flagged SLOW. Handy to call from a REPL/console after noticing the
    dashboard felt sluggish, without having to go find the log file.
    """
    try:
        with open(_LOG_PATH) as f:
            lines = [line.rstrip("\n") for line in f if " SLOW " in line]
        return lines[-limit:]
    except FileNotFoundError:
        return []


def log_path():
    """Where the SSH call log lives, for reference."""
    return _LOG_PATH


def _ssh_opts(conn):
    return [
        "-p", str(conn.get("port", 22)),
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-o", f"ConnectTimeout={CONNECT_TIMEOUT}",
        "-o", "BatchMode=no",
        "-o", "ControlMaster=auto",
        "-o", f"ControlPersist={CONTROL_PERSIST}",
        "-o", f"ControlPath={_control_path(conn)}",
    ]


class RemoteResult:
    """Structured result of a remote command.

    error_kind is one of:
        None          - success (ok is True)
        "offline"     - could not reach the host at all (refused/no route/DNS)
        "timeout"     - connection or command took too long
        "auth"        - SSH authentication failed
        "not_found"   - sshpass/ssh not installed on the laptop itself
        "error"       - command ran but returned a non-zero exit code,
                         or something else unexpected happened
    """

    def __init__(self, ok, stdout="", stderr="", returncode=None, error_kind=None):
        self.ok = ok
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.error_kind = error_kind

    def __repr__(self):
        return (
            f"RemoteResult(ok={self.ok}, error_kind={self.error_kind!r}, "
            f"returncode={self.returncode!r}, stdout={self.stdout[:60]!r})"
        )

    # Convenience for services that just want a status word when things
    # go wrong, e.g. `return result.stdout if result.ok else result.status_word()`
    def status_word(self):
        return {
            "offline": "Offline",
            "timeout": "Timeout",
            "auth": "Auth Error",
            "not_found": "SSH Unavailable",
            "error": "Unknown",
        }.get(self.error_kind, "Unknown")


def _build_command(command):
    if isinstance(command, (list, tuple)):
        return " ".join(shlex.quote(part) for part in command)
    return command


def warm_connection(nano: Optional[str] = None, timeout: int = 10) -> RemoteResult:
    """Establish (or confirm) the shared background SSH connection for a
    Nano ahead of time, so the first real service call doesn't have to
    absorb the full connection-setup cost inside its own (often tighter)
    timeout.

    Call this once at app/dashboard startup (and optionally again if a
    Nano was previously offline and might have come back). Safe to call
    repeatedly - if the master connection is already up, this is nearly
    instant.
    """
    return run_remote(["true"], nano=nano, timeout=timeout)


def close_connection(nano: Optional[str] = None) -> None:
    """Tear down the shared background SSH connection for a Nano, e.g. on
    app shutdown. Not required for correctness (ControlPersist will expire
    it on its own), but tidy for a clean exit.
    """
    conn = get_nano(nano)
    argv = [
        "ssh", "-O", "exit",
        "-o", f"ControlPath={_control_path(conn)}",
        f"{conn['user']}@{conn['host']}",
    ]
    try:
        subprocess.run(argv, capture_output=True, timeout=5)
    except Exception:
        pass


def run_remote(
    command: Union[str, List[str]],
    nano: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> RemoteResult:
    """Run a command on the configured NanoPC over SSH and return the result.

    `command` can be a plain string (may include pipes/redirects - it is
    executed as-is by the remote shell) or a list of args (each arg is
    shell-quoted and joined, for callers that build commands piece by piece).

    Every call is timed and logged (see _log_call/log_path/recent_slow_calls
    above) so slow calls can be traced back to a specific command later.
    """
    conn = get_nano(nano)
    start = time.monotonic()
    result = _run_remote_impl(command, conn, timeout)
    duration = time.monotonic() - start
    _log_call(conn, command, duration, result)
    return result


def _run_remote_impl(
    command: Union[str, List[str]],
    conn: dict,
    timeout: int,
) -> RemoteResult:
    remote_command = _build_command(command)

    argv = [
        "sshpass", "-p", conn["password"],
        "ssh", *_ssh_opts(conn),
        f"{conn['user']}@{conn['host']}",
        remote_command,
    ]

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""

        if result.returncode == 0:
            return RemoteResult(True, stdout=stdout, stderr=stderr, returncode=0)

        # ssh itself uses exit code 255 for connection-level failures
        # (as opposed to the remote command's own non-zero exit code).
        if result.returncode == 255:
            lowered = stderr.lower()

            if "permission denied" in lowered or "authentication" in lowered:
                kind = "auth"
            elif (
                "connection refused" in lowered
                or "no route to host" in lowered
                or "could not resolve" in lowered
                or "network is unreachable" in lowered
            ):
                kind = "offline"
            elif "timed out" in lowered or "timeout" in lowered:
                kind = "timeout"
            else:
                kind = "offline"

            return RemoteResult(
                False, stdout=stdout, stderr=stderr,
                returncode=result.returncode, error_kind=kind,
            )

        # Remote command itself ran but returned non-zero - this is a
        # legitimate result for some commands (e.g. "ufw status" style
        # checks), so hand it back as-is and let the caller interpret it.
        return RemoteResult(
            False, stdout=stdout, stderr=stderr,
            returncode=result.returncode, error_kind="error",
        )

    except subprocess.TimeoutExpired:
        return RemoteResult(False, error_kind="timeout")

    except FileNotFoundError:
        # sshpass (or ssh) is not installed on the laptop
        return RemoteResult(False, error_kind="not_found")

    except Exception as e:
        return RemoteResult(False, stderr=str(e), error_kind="error")


def read_remote_file(path: str, nano: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT) -> RemoteResult:
    """Read a text file on the Nano (equivalent of open(path).read())."""
    return run_remote(["cat", path], nano=nano, timeout=timeout)


def query_remote_sqlite(
    db_path: str,
    sql: str,
    params: Optional[list] = None,
    nano: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
):
    """Run a read query against a sqlite database on the Nano and return
    a list of rows (each row a list of values), similar to cursor.fetchall().

    Executed via a small python3 one-liner on the Nano itself (sqlite3 is
    part of the Python standard library, so this does not require the
    Nano to have the `sqlite3` CLI installed) which prints the result as
    JSON, which we then parse on the laptop.

    Returns None on failure - callers should treat that the same way they
    used to treat a sqlite3.Error/exception.
    """

    script = (
        "import sqlite3, json, sys; "
        f"conn = sqlite3.connect({db_path!r}); "
        "cur = conn.cursor(); "
        f"cur.execute({sql!r}, {params or []!r}); "
        "rows = cur.fetchall(); "
        "conn.close(); "
        "print(json.dumps(rows))"
    )

    result = run_remote(["python3", "-c", script], nano=nano, timeout=timeout)

    if not result.ok:
        return None

    try:
        return json.loads(result.stdout)
    except Exception:
        return None


def query_remote_sqlite_dicts(
    db_path: str,
    sql: str,
    params: Optional[list] = None,
    nano: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
):
    """Like query_remote_sqlite, but returns a list of dicts (column name ->
    value) instead of a list of plain rows - equivalent to using
    sqlite3.Row as the row_factory. Returns None on failure.
    """

    script = (
        "import sqlite3, json; "
        f"conn = sqlite3.connect({db_path!r}); "
        "cur = conn.cursor(); "
        f"cur.execute({sql!r}, {params or []!r}); "
        "cols = [d[0] for d in cur.description]; "
        "rows = [dict(zip(cols, row)) for row in cur.fetchall()]; "
        "conn.close(); "
        "print(json.dumps(rows))"
    )

    result = run_remote(["python3", "-c", script], nano=nano, timeout=timeout)

    if not result.ok:
        return None

    try:
        return json.loads(result.stdout)
    except Exception:
        return None


def execute_remote_sqlite(
    db_path: str,
    sql: str,
    params: Optional[list] = None,
    nano: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> bool:
    """Run a write (UPDATE/INSERT/DELETE) query against a sqlite database
    on the Nano. Returns True if at least one row was affected.
    """

    script = (
        "import sqlite3, json; "
        f"conn = sqlite3.connect({db_path!r}, timeout=10); "
        "cur = conn.cursor(); "
        f"cur.execute({sql!r}, {params or []!r}); "
        "conn.commit(); "
        "updated = cur.rowcount; "
        "conn.close(); "
        "print(json.dumps(updated))"
    )

    result = run_remote(["python3", "-c", script], nano=nano, timeout=timeout)

    if not result.ok:
        return False

    try:
        return int(result.stdout) > 0
    except Exception:
        return False
