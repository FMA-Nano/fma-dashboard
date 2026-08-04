import sqlite3
import os


DB_PATH = os.path.expanduser(
    "~/ST500V3/Main/app.db"
)


PUMP_STATUS = {

    0: "Error",
    1: "Idle",
    2: "Call",
    3: "Busy",
    4: "Finished",
    5: "Alone",
    6: "Leak",
    7: "Pulse Error",
    8: "Authorizing",
    9: "Paused",
    15: "Price",
    51: "Power Error",
    52: "Down",
    96: "Communication Error",
    97: "Echo",
    98: "Unknown",
    99: "Tag",
    100: "Manual Tag",
    146: "Ghost",
    147: "Bypass",
    200: "Communicating",

}



def get_status_text(status):

    try:
        status = int(status)

    except:
        return "Unknown"


    return PUMP_STATUS.get(
        status,
        "Unknown"
    )



class Pump:

    def __init__(self):

        self.id = 0
        self.status = 0
        self.status_text = ""

        self.pulse_rate = ""
        self.pulse_timeout = ""

        self.auto_authorize = ""

        self.hardware_id = ""
        self.linked_tank = ""



def get_pumps():

    pumps = []


    try:

        conn = sqlite3.connect(
            DB_PATH
        )

        cursor = conn.cursor()


        cursor.execute(
            """
            SELECT
                id,
                Status,
                PulsRate,
                PulseTimeout,
                Authorized,
                HardwareId,
                tank_id

            FROM Pumps

            ORDER BY id
            """
        )


        rows = cursor.fetchall()


        for row in rows:


            pump = Pump()


            pump.id = row[0]

            pump.status = row[1]

            pump.status_text = get_status_text(
                row[1]
            )


            pump.pulse_rate = row[2]

            pump.pulse_timeout = row[3]

            pump.auto_authorize = row[4]

            pump.hardware_id = row[5]

            pump.linked_tank = row[6]


            pumps.append(
                pump
            )


        conn.close()


    except Exception as e:

        print(
            "Pump database error:",
            e
        )


    return pumps