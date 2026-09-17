"""Helpers for detecting when the dashboard is running directly on a
NanoPC (rather than on a laptop connecting to one remotely), and for
figuring out which local address to SSH into for a "connect to this
device" quick-connect flow.
"""

import socket


def is_running_on_nano():
    """Check whether the machine the dashboard itself is running on is
    a NanoPC board. Used to decide whether to show/label a "connect to
    this device" shortcut on the login screen.
    """
    try:
        with open("/proc/device-tree/model") as f:
            model = f.read()
        return "nanopc" in model.lower()
    except Exception:
        return False


def get_local_candidate_hosts():
    """Return a list of addresses this machine can plausibly be reached
    at over SSH, loopback first, in the order a "connect to this
    device" flow should try them.

    Uses psutil (already a project dependency) for interface
    enumeration - works the same way regardless of platform, though
    this feature is really only meaningful when actually run on the
    Nano itself.

    Deliberately excludes known virtual/container/VPN/tunnel interfaces
    (Docker bridges, veth pairs, Tailscale, WireGuard, libvirt's virbr0,
    etc) since a real device typically has several of these active and
    none of them are anything you'd actually SSH into. Real network
    interfaces are matched by prefix (covers both legacy names like
    "eth0"/"wlan0" and modern "predictable" names like "enp7s0"/
    "wlp8s0"/"wlx...") rather than requiring an exact "eth0"/"wlan0"
    match, which otherwise silently misses most current Linux systems.
    """

    candidates = ["127.0.0.1"]
    seen = set(candidates)

    virtual_prefixes = (
        "veth", "docker", "br-", "virbr", "tailscale", "wg", "tun",
        "tap", "vmnet", "vboxnet", "utun", "bridge", "zt",
    )
    wired_wireless_prefixes = ("eth", "en", "wl")

    def is_virtual(name):
        lname = name.lower()
        return any(lname.startswith(p) for p in virtual_prefixes)

    try:
        import psutil
        addrs = psutil.net_if_addrs()

        def add_from(iface_name):
            for addr in addrs.get(iface_name, []):
                if addr.family == socket.AF_INET and addr.address not in seen:
                    candidates.append(addr.address)
                    seen.add(addr.address)

        real_interfaces = [
            name for name in addrs
            if name != "lo" and not is_virtual(name)
        ]

        # Recognizable wired/wireless interfaces first (covers both
        # old-style and modern predictable naming), anything else
        # unrecognized as a lower-priority fallback.
        preferred = [n for n in real_interfaces if n.lower().startswith(wired_wireless_prefixes)]
        other = [n for n in real_interfaces if n not in preferred]

        for name in preferred:
            add_from(name)
        for name in other:
            add_from(name)

    except Exception:
        pass

    return candidates
