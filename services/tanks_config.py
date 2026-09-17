"""Tank configuration service.

Migrated to remote execution: app.db lives on the Nano, so reads/writes
now go over SSH. get_tanks_config() returns a list of dicts, matching
how the screen already indexes rows by key with sqlite3.Row locally.
"""

from services.remote import query_remote_sqlite_dicts, execute_remote_sqlite
from services.config import APP_DB_PATH

DB_PATH = APP_DB_PATH


def get_tanks_config():

    rows = query_remote_sqlite_dicts(
        DB_PATH,
        """
        SELECT
            id,
            TankNo,
            ProbeId,
            Downloaded
        FROM Tanks
        ORDER BY TankNo
        """,
    )

    return rows if rows is not None else []


def update_tank_config(
        tank_id,
        probe_id,
):

    try:
        return execute_remote_sqlite(
            DB_PATH,
            """
            UPDATE Tanks
            SET
                ProbeId = ?,
                Downloaded = 0
            WHERE id = ?
            """,
            [
                probe_id,
                tank_id
            ],
        )

    except Exception as e:

        print(f"Tank config update failed: {e}")

        return False
