"""Tank status service.

Migrated to remote execution: app.db lives on the Nano, so it's now
queried over SSH instead of opened directly with sqlite3 locally.
"""

from services.remote import query_remote_sqlite
from services.config import APP_DB_PATH

DB_PATH = APP_DB_PATH


class Tank:

    def __init__(self):

        self.id = 0

        self.tank_number = 0
        self.grade_id = 0

        self.capacity = 0
        self.level = 0

        self.volume = 0
        self.ullage = 0

        self.temperature = 0
        self.water = 0

        self.web_id = 0
        self.client_id = ""

        self.site_recon_id = 0
        self.probe_id = 0

        self.downloaded = False
        self.enabled = False


def get_tanks():

    tanks = []

    rows = query_remote_sqlite(
        DB_PATH,
        """
        SELECT
            id,
            TankNo,
            grade_id,
            Capacity,
            Level,
            client_id,
            Volume,
            Ullage,
            Temperature,
            Water,
            WebId,
            DownLoaded,
            SiteReconId,
            ProbeId,
            enabled

        FROM Tanks

        ORDER BY CAST(TankNo AS INTEGER)
        """,
    )

    if rows is None:
        print("Tank database error: could not reach Nano/query app.db")
        return tanks

    for row in rows:

        tank = Tank()

        tank.id = row[0]
        tank.tank_number = row[1]
        tank.grade_id = row[2]

        tank.capacity = row[3]
        tank.level = row[4]

        tank.client_id = row[5]

        tank.volume = row[6]
        tank.ullage = row[7]

        tank.temperature = row[8]
        tank.water = row[9]

        tank.web_id = row[10]
        tank.downloaded = bool(row[11])

        tank.site_recon_id = row[12]
        tank.probe_id = row[13]

        tank.enabled = bool(row[14])

        tanks.append(tank)

    return tanks
