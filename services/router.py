import sqlite3
import json

APP_DB = "/home/pi/ST500V3/Main/app.db"


def get_router_modem_status():

    try:
        connection = sqlite3.connect(APP_DB)
        cursor = connection.cursor()

        cursor.execute("""
            SELECT TypeString
            FROM Config
            WHERE id = 68
              AND FieldName = 'RouterModemStatus'
            LIMIT 1
        """)

        row = cursor.fetchone()
        connection.close()

        if not row or not row[0]:
            return {}

        data = json.loads(row[0])

        # -----------------------------------------
        # Modem status
        # -----------------------------------------

        modem = data.get("Modem")

        if modem == "1":
            data["Modem"] = "Connected"
        else:
            data["Modem"] = "Disconnected"

            # If modem is disconnected,
            # all modem-related information is unavailable.
            for key in data:
                if key != "Modem":
                    data[key] = "N/A"

            return data

        # -----------------------------------------
        # SIM status
        # -----------------------------------------

        if data.get("SIM") == "1":
            data["SIM"] = "Inserted"
        else:
            data["SIM"] = "Not Inserted"

        # -----------------------------------------
        # SIM Flag
        # -----------------------------------------

        if data.get("SIM Flag") == "1":
            data["SIM Flag"] = "Ready"
        else:
            data["SIM Flag"] = "Not Ready"

        # -----------------------------------------
        # Connection
        # -----------------------------------------

        if data.get("Connection") == "1":
            data["Connection"] = "Connected"
        else:
            data["Connection"] = "Disconnected"

        # -----------------------------------------
        # Network
        # -----------------------------------------

        if not data.get("Network"):
            data["Network"] = "Not Connected"

        # -----------------------------------------
        # Empty values
        # -----------------------------------------

        for key in data:
            if data[key] == "":
                data[key] = "N/A"

        return data

    except Exception as e:
        print(f"Router status error: {e}")
        return {}