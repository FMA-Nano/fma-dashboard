import sqlite3

DB_PATH = "/home/pi/ST500V3/Main/app.db"


def get_tanks_config():

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            TankNo,
            ProbeId,
            Downloaded
        FROM Tanks
        ORDER BY TankNo
        """
    )

    tanks = cursor.fetchall()

    conn.close()

    return tanks


def update_tank_config(
        tank_id,
        probe_id,
):

    try:

        conn = sqlite3.connect(
            DB_PATH,
            timeout=10
        )

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE Tanks
            SET
                ProbeId = ?,
                Downloaded = 0
            WHERE id = ?
            """,
            (
                probe_id,
                tank_id
            )
        )

        conn.commit()

        updated = cursor.rowcount

        conn.close()

        return updated > 0

    except Exception as e:

        print(f"Tank config update failed: {e}")

        return False