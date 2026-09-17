"""Pump configuration service.

Migrated to remote execution: app.db lives on the Nano, so reads/writes
now go over SSH. get_pumps_config() returns a list of dicts (column name
-> value), matching how the screen already indexes rows by key
(pump["id"], etc) with sqlite3.Row locally.
"""

from services.remote import query_remote_sqlite_dicts, execute_remote_sqlite
from services.config import APP_DB_PATH

DB_PATH = APP_DB_PATH


def get_pumps_config():

    rows = query_remote_sqlite_dicts(
        DB_PATH,
        """
        SELECT
            id,
            HardwareId,
            PulsRate,
            Downloaded
        FROM Pumps
        ORDER BY id
        """,
    )

    return rows if rows is not None else []


def update_pump_config(
        pump_id,
        hardware_id,
        pulse_rate
):

    try:
        return execute_remote_sqlite(
            DB_PATH,
            """
            UPDATE Pumps
            SET
                HardwareId = ?,
                PulsRate = ?,
                Downloaded = 0
            WHERE id = ?
            """,
            [
                hardware_id,
                pulse_rate,
                pump_id
            ],
        )

    except Exception as e:

        print(
            f"Pump config update failed: {e}"
        )

        return False
