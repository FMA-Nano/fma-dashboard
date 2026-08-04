import subprocess


def get_user_cron():

    jobs = []

    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            timeout=3
        )

        if result.returncode == 0:
            for line in result.stdout.splitlines():

                line = line.strip()

                if line and not line.startswith("#"):
                    jobs.append(line)

    except Exception:
        pass

    return jobs



def get_root_cron():

    jobs = []

    try:
        result = subprocess.run(
            ["sudo", "crontab", "-l"],
            capture_output=True,
            text=True,
            timeout=3
        )

        if result.returncode == 0:
            for line in result.stdout.splitlines():

                line = line.strip()

                if line and not line.startswith("#"):
                    jobs.append(line)

    except Exception:
        pass

    return jobs