"""Log Files browser service.

/home/pi/ST500V3/LogFiles/ contains one subfolder per subsystem (Pumps,
Tanks, etc), each holding:
  - info.log            - today's log, plain text
  - info.log.<date>.zip - older days, rotated into a zip to save space

Rather than downloading/extracting anything, both cases are read
directly on the Nano and streamed back over SSH: plain files via `cat`,
zips via `unzip -p` (extract-to-stdout, nothing written to disk). This
also sidesteps the odd behavior of manually unzipping these archives
(they come out as an extension-less file that gets misidentified as a
generic/binary "program" file by most file managers) - we never
actually extract them anywhere, just stream their text content.

Output is capped to the last TAIL_LINES lines by default, since a full
day's log could be large and the most recent entries are almost always
what's actually useful to see first.
"""

from services.remote import run_remote

LOG_FILES_ROOT = "/home/pi/ST500V3/LogFiles"

TAIL_LINES = 500


def list_log_folders():
    """Return the list of subfolder names directly under LogFiles/ (e.g.
    ["Pumps", "Tanks", ...]), or None on failure.
    """

    result = run_remote(
        ["find", LOG_FILES_ROOT, "-mindepth", "1", "-maxdepth", "1", "-type", "d", "-printf", "%f\\n"],
        timeout=8,
    )

    if not result.ok:
        return None

    folders = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return sorted(folders)


def list_log_files(folder):
    """Return the list of files directly inside LogFiles/<folder>/, each
    as {"name": ..., "size": <bytes>, "modified": "YYYY-MM-DD HH:MM"},
    most recently modified first. Returns None on failure.
    """

    folder_path = f"{LOG_FILES_ROOT}/{folder}"

    result = run_remote(
        ["find", folder_path, "-mindepth", "1", "-maxdepth", "1", "-type", "f",
         "-printf", "%f|%s|%TY-%Tm-%Td %TH:%TM\\n"],
        timeout=8,
    )

    if not result.ok:
        return None

    files = []

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) != 3:
            continue
        name, size, modified = parts
        try:
            size = int(size)
        except ValueError:
            size = 0
        files.append({"name": name, "size": size, "modified": modified})

    files.sort(key=lambda f: f["modified"], reverse=True)
    return files


def read_log_file(folder, filename, tail_lines=TAIL_LINES):
    """Return LogFiles/<folder>/<filename>'s content as a string.
    Transparently handles both plain text files (cat/tail) and .zip
    archives (unzip -p, streamed straight to stdout - nothing is written
    to disk on the Nano, so there's no extension-less extracted file
    left behind to worry about).

    tail_lines caps the output to that many of the most recent lines;
    pass None for the full file with no limit at all.

    Returns None on failure (offline, file not found, etc).
    """

    file_path = f"{LOG_FILES_ROOT}/{folder}/{filename}"
    is_zip = filename.lower().endswith(".zip")

    if tail_lines is None:
        # No limit - just stream the whole thing.
        command = (
            f"unzip -p {_shell_quote(file_path)}" if is_zip
            else f"cat {_shell_quote(file_path)}"
        )
    else:
        tail_lines = int(tail_lines)
        command = (
            f"unzip -p {_shell_quote(file_path)} | tail -n {tail_lines}" if is_zip
            else f"tail -n {tail_lines} {_shell_quote(file_path)}"
        )

    # Uncapped reads can take a while on a large file over a slow link -
    # give it more room than the default before giving up.
    timeout = 30 if tail_lines is None else 15

    result = run_remote(command, timeout=timeout)

    if not result.ok:
        return None

    return result.stdout


def _shell_quote(value):
    """Minimal single-quote shell escaping for a path we're embedding in
    a pipeline string (run_remote's list form can't express a pipe, so
    this command has to be built as a single string instead).
    """
    return "'" + value.replace("'", "'\\''") + "'"
