from textual.containers import VerticalScroll
from textual.widgets import Static

from widgets.header import LOGO
from version import VERSION, BUILD, DATE_UPDATED, VENDOR


class AboutPage(VerticalScroll):

    def compose(self):

        yield Static(
            "[bold]About[/bold]",
            classes="page-title"
        )

        yield Static(LOGO)

        yield Static(
            f"Version        {VERSION}\n"
            f"Date Updated   {DATE_UPDATED}\n"
            f"Build          {BUILD}\n"
            f"Vendor         {VENDOR}\n",
            classes="info-block",
        )

        yield Static(
            "[bold]Version History[/bold]",
            classes="page-title"
        )

        yield Static(
            "0.3.50  Fixed Nano/Software headings stretching full-width; added persistent Lost Connection banner (stays until reconnected).\n"
            "0.3.49  Added Nano heading + Restart button to header (reboots the Nano itself, distinct from Software Restart).\n"
            "0.3.48  Fixed Restart Software path - runs from /home/pi/ (was incorrectly /home/pi/ST500V3).\n"
            "0.3.47  LCD Settings simplified (Enable/Disable buttons, cleaner state display); reduced spacing between sections.\n"
            "0.3.46  Added Software section to header (Restart / Stop All), mirroring the on-device admin menu.\n"
            "0.3.45  Added LCD Settings (admin menu on/off) to Router Settings, with reboot confirmation.\n"
            "0.3.44  Log Files: full-screen viewer (pick a day from a dropdown), fixed the scroll bug stuck at ~20 lines.\n"
            "0.3.43  Log Files: normal-sized buttons, folder grid layout, and a Lines/All control for viewing content.\n"
            "0.3.42  Added Log Files sidebar page - browse folders/files and view content (tested end-to-end with Pumps/info.log).\n"
            "0.3.41  Added red/green update-status dot to every card's title, showing if the last refresh succeeded.\n"
            "0.3.40  Reverted button size back to the confirmed-working small (1-row) version.\n"
            "0.3.39  Fixed button label sitting at the top instead of centered (explicit content-align).\n"
            "0.3.38  Fixed crash on Rebooted/marker rows in Data Usage history; buttons made bigger (height 2).\n"
            "0.3.37  Found the real cause of button clipping: Textual's default 3-row button height (line-pad); forced buttons to 1 row.\n"
            "0.3.36  Removed bottom padding that was shrinking the visible area; used a trailing spacer instead.\n"
            "0.3.35  Divider now spans full width (was a fixed-length string); more bottom padding on Router Settings.\n"
            "0.3.34  Added divider + spacing between APN and Time Settings, fixed Sync RTC button being cut off.\n"
            "0.3.33  Fixed Router Settings page not scrolling (missing height CSS); page title reverted to Router Settings.\n"
            "0.3.32  Renamed Router Settings to Settings, added Time Settings (sync RTC with local time).\n"
            "0.3.31  Added Date Time Info card (timedatectl) to System Information.\n"
            "0.3.30  Added APN display + new Router Settings page (change/save APN, reboot router).\n"
            "0.3.29  Added SIM CCID to Router / Modem card.\n"
            "0.3.28  (reverted) Connection status indicator - didn't work, will revisit.\n"
            "0.3.27  Header rows now colored blue like section headings, detail rows more indented.\n"
            "0.3.26  Header rows now align with detail rows below them; By Application columns aligned too.\n"
            "0.3.25  Added | separators to Data Usage header rows to match detail rows.\n"
            "0.3.24  Data Usage history is now an aligned table, file usage shows the actual command.\n"
            "0.3.23  Added Program Usage and File Usage history (today only) to Data Usage page.\n"
            "0.3.22  Added Data Usage sidebar page - today's totals by application.\n"
            "0.3.21  Added UPS Monitor service status to Programs cards.\n"
            "0.3.20  Added UPS (UPS6910C-24) status card to Dashboard.\n"
            "0.3.19  Fixed status value alignment - column width now auto-sizes per card.\n"
            "0.3.18  Renamed Programs card, dropped Router Modem Service, SSH/Data Monitor now show Active/Inactive.\n"
            "0.3.17  Added Router Modem Timer boot-enabled status - the real answer to \"will it survive a reboot?\"\n"
            "0.3.16  Fixed \"static\" showing as Unknown for timer-triggered services.\n"
            "0.3.15  Added Router Modem service/timer status to Programs.\n"
            "0.3.14  Backfilled version history and added this section.\n"
            "0.3.13  Added red status color for Not Inserted / Not Connected / Disconnected.\n"
            "0.3.12  Added Refresh button on top right.\n"
            "0.3.11  Added \"Password is required\" validation on connect.\n"
            "0.3.10  Saved sites no longer store passwords on disk.\n"
            "0.3.09  Added interface IP + metric to Dashboard Network card.\n"
            "0.3.08  Added route metric to Network screen's Interfaces list.\n"
            "0.3.07  Blue headings for Pumps/Tanks, Network sections, Security.\n"
            "0.3.06  Added \"Coms / Programs\" section heading on Dashboard.\n"
            "0.3.05  Fixed Dashboard cards going stale after reorganizing layout.\n"
            "0.3.04  Merged WiFi/Hotspot into Network card, Services into Programs card.\n"
            "0.3.03  Restructured Dashboard into System Information / Network sections.\n"
            "0.3.02  Added Quit button on login screen.\n"
            "0.3.01  Started version tracking.\n",
        )