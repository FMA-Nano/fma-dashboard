# Default settings

refresh_interval = 5
auto_refresh = True


# -----------------------------
# Refresh Interval
# -----------------------------

def get_refresh_interval():
    return refresh_interval



def set_refresh_interval(value):
    global refresh_interval

    refresh_interval = int(value)



# -----------------------------
# Auto Refresh
# -----------------------------

def get_auto_refresh():
    return auto_refresh



def set_auto_refresh(value):
    global auto_refresh

    auto_refresh = bool(value)