"""Central configuration for remote NanoPC connections.

Kept as a dict keyed by name so that adding a second/third Nano later
does not require touching every service - callers can eventually pass a
`nano` name through to run_remote()/services, defaulting to DEFAULT_NANO.

The active connection (currently just "default") can be changed at
runtime via set_nano() - e.g. from the Settings screen when someone
points the dashboard at a different site - and optionally persisted to
disk so the choice survives an app restart.
"""

import json
import os

DEFAULT_NANO = "default"
DEFAULT_PORT = 22

# Hardcoded fallback used the very first time the app runs (before any
# saved connection file exists).
NANOS = {
    "default": {
        "host": "172.16.70.3",
        "port": DEFAULT_PORT,
        "user": "pi",
        "password": "pi",
    },
}

# Shared paths on the Nano (used by multiple services)
APP_DB_PATH = "/home/pi/ST500V3/Main/app.db"

# Where a chosen connection is saved so it survives an app restart.
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".fma_dashboard", "connection.json")

# A named list of sites the person has saved for quick reconnecting,
# e.g. multiple field sites all reachable at pi@remote.fmafrica.com with
# different ports.
SITES_FILE = os.path.join(os.path.expanduser("~"), ".fma_dashboard", "sites.json")


def get_nano(name=None):
    """Return the connection dict for a configured Nano."""
    return NANOS[name or DEFAULT_NANO]


def set_nano(host, port=DEFAULT_PORT, user="pi", password="", name=None):
    """Update a Nano's connection info at runtime.

    Every service calls run_remote() without specifying `nano`, so
    updating the "default" entry immediately redirects all of them to
    the new target - no need to touch individual services.
    """

    try:
        port = int(port)
    except (TypeError, ValueError):
        port = DEFAULT_PORT

    NANOS[name or DEFAULT_NANO] = {
        "host": host.strip(),
        "port": port,
        "user": user.strip() or "pi",
        "password": password,
    }

    return NANOS[name or DEFAULT_NANO]


def save_nano(name=None):
    """Persist the given (or default) Nano's connection info to disk so
    it's remembered next time the app starts. Returns True on success.
    """
    conn = get_nano(name)

    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(conn, f)
        return True
    except Exception:
        return False


def load_saved_nano(name=None):
    """Load a previously-saved connection from disk, if one exists, and
    make it the active connection. Returns the loaded dict, or None if
    there was nothing saved (in which case the hardcoded default above
    stays active).
    """
    try:
        with open(CONFIG_FILE) as f:
            saved = json.load(f)
    except Exception:
        return None

    if not saved.get("host"):
        return None

    return set_nano(
        host=saved.get("host", ""),
        port=saved.get("port", DEFAULT_PORT),
        user=saved.get("user", "pi"),
        password=saved.get("password", ""),
        name=name,
    )


# Load a previously-saved connection (if any) as soon as this module is
# imported, so every service picks it up automatically without every
# entry point needing to remember to call this.
load_saved_nano()


# ---------------------------------------------------------------------------
# Saved sites - a named list of connections for quick switching between
# multiple field sites, separate from the single "active" connection above.
# ---------------------------------------------------------------------------

def list_sites():
    """Return the saved site list as [{"name", "host", "port", "user",
    "password"}, ...], sorted by name. Empty list if nothing saved yet.
    """
    return sorted(_load_sites(), key=lambda s: s.get("name", "").lower())


def list_sites_by_recency():
    """Return the saved site list with the most recently added/updated
    site first - used by the UI so a freshly-saved site appears at the
    top of the list, right under the Save button, instead of wherever
    alphabetical order would put it.
    """
    return list(reversed(_load_sites()))


def _load_sites():
    try:
        with open(SITES_FILE) as f:
            sites = json.load(f)
    except Exception:
        return []

    if not isinstance(sites, list):
        return []

    return sites


def get_site(name):
    """Return a single saved site by name, or None if not found."""
    for site in list_sites():
        if site.get("name") == name:
            return site
    return None


def save_site(name, host, port=DEFAULT_PORT, user="pi", password=""):
    """Add or update a saved site by name. Returns True on success.

    Deliberately never stores the password, even if one is passed in -
    saved sites are meant for quickly recalling host/port/user, not for
    persisting credentials to disk. Selecting a saved site always leaves
    the password blank, requiring it to be typed in each time.
    """

    name = (name or "").strip()

    if not name or not host.strip():
        return False

    try:
        port = int(port)
    except (TypeError, ValueError):
        port = DEFAULT_PORT

    sites = _load_sites()
    sites = [s for s in sites if s.get("name") != name]
    sites.append({
        "name": name,
        "host": host.strip(),
        "port": port,
        "user": user.strip() or "pi",
        "password": "",
    })

    try:
        os.makedirs(os.path.dirname(SITES_FILE), exist_ok=True)
        with open(SITES_FILE, "w") as f:
            json.dump(sites, f)
        return True
    except Exception:
        return False


def delete_site(name):
    """Remove a saved site by name. Returns True on success (including
    if the site didn't exist)."""

    sites = [s for s in _load_sites() if s.get("name") != name]

    try:
        os.makedirs(os.path.dirname(SITES_FILE), exist_ok=True)
        with open(SITES_FILE, "w") as f:
            json.dump(sites, f)
        return True
    except Exception:
        return False


def _scrub_saved_site_passwords():
    """One-time cleanup: any site saved before passwords stopped being
    persisted may still have one sitting in the file on disk - blank
    those out immediately rather than waiting for each site to be
    re-saved individually.
    """
    try:
        sites = _load_sites()
    except Exception:
        return

    if not sites:
        return

    changed = False
    for site in sites:
        if site.get("password"):
            site["password"] = ""
            changed = True

    if not changed:
        return

    try:
        os.makedirs(os.path.dirname(SITES_FILE), exist_ok=True)
        with open(SITES_FILE, "w") as f:
            json.dump(sites, f)
    except Exception:
        pass


# Run once at import time so any passwords saved before this change
# existed get cleared out immediately, not just on next save.
_scrub_saved_site_passwords()
