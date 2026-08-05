import sqlite3


DB_PATH = "/home/pi/ST500V3/Main/app.db"



def get_pumps_config():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()


    cursor.execute(
        """
        SELECT
            id,
            HardwareId,
            PulsRate,
            Downloaded
        FROM Pumps
        ORDER BY id
        """
    )


    pumps = cursor.fetchall()


    conn.close()


    return pumps





def update_pump_config(
        pump_id,
        hardware_id,
        pulse_rate
):

    try:

        conn = sqlite3.connect(
            DB_PATH,
            timeout=10
        )


        cursor = conn.cursor()


        cursor.execute(
            """
            UPDATE Pumps
            SET
                HardwareId = ?,
                PulsRate = ?,
                Downloaded = 0
            WHERE id = ?
            """,
            (
                hardware_id,
                pulse_rate,
                pump_id
            )
        )


        conn.commit()


        updated = cursor.rowcount


        conn.close()


        return updated > 0



    except Exception as e:

        print(
            f"Pump config update failed: {e}"
        )

        return False