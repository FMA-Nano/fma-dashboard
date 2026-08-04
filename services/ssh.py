import subprocess
import datetime


def get_ssh_status():

    try:

        result = subprocess.run(
            [
                "systemctl",
                "is-active",
                "ssh"
            ],
            capture_output=True,
            text=True,
            timeout=3
        )

        status = result.stdout.strip()

        if status == "active":
            return "Enabled"

        elif status == "inactive":
            return "Disabled"

        return "Unknown"
    
    except Exception:

        return "Unknown"


def get_ssh_service():

    try:

        result = subprocess.run(
            [
                "systemctl",
                "is-enabled",
                "ssh"
            ],
            capture_output=True,
            text=True,
            timeout=3
        )

        status = result.stdout.strip()

        if status == "enabled":
            return "Enabled"

        elif status == "disabled":
            return "Disabled"

        return "Unknown"

    except Exception:

        return "Unknown"
    
    
def get_ssh_history(limit=25):

    try:

        cmd = (
            "sudo journalctl -u ssh "
            "| grep -E 'Accepted password|Failed password|Invalid user|Disconnected from|Connection closed|PAM.*authentication failures' "
            "| tail -" + str(limit)
        )


        result = subprocess.check_output(
            cmd,
            shell=True,
            text=True
        )


        logs = []


        for line in result.splitlines():

            parts = line.split()


            if len(parts) < 6:
                continue


            # -------------------------
            # Date and time
            # -------------------------

            month = parts[0]
            day = parts[1]
            time = parts[2]


            try:

                year = datetime.datetime.now().year

                date = datetime.datetime.strptime(
                    f"{month} {day} {year}",
                    "%b %d %Y"
                ).strftime(
                    "%d %b %Y"
                )

            except:

                date = f"{day} {month}"



            # -------------------------
            # Remove:
            # PC4-01-08-19
            # sshd[1234]:
            # -------------------------

            description = " ".join(parts[5:])



            # -------------------------
            # Determine event
            # -------------------------

            if "Accepted" in description:

                event = "LOGIN"

            elif "Failed" in description:

                event = "FAILED"

            elif "Disconnected" in description:

                event = "DISCONNECT"

            elif "session closed" in description:

                event = "CLOSED"

            elif "PAM" in description and "authentication failures" in description:
                event = "CRITICAL"
                
            else:
                event = "UNKNOWN"



            # -------------------------
            # Store
            # -------------------------

            logs.append(
                {
                    "date": date,
                    "time": time,
                    "event": event,
                    "description": description
                }
            )



        # newest first

        return logs[::-1]



    except Exception as e:

        return [
            {
                "date": "-",
                "time": "-",
                "event": "ERROR",
                "description": str(e)
            }
        ]