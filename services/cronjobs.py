"""Cron job listing service.

Migrated to remote execution: crontab describes the Nano's scheduled
jobs, so it now runs on the Nano over SSH.
"""

from services.remote import run_remote


def _parse_jobs(output):
    jobs = []
    for line in output.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            jobs.append(line)
    return jobs


def get_user_cron():

    result = run_remote(["crontab", "-l"], timeout=3)

    if result.returncode == 0:
        return _parse_jobs(result.stdout)

    return []


def get_root_cron():

    result = run_remote(["sudo", "crontab", "-l"], timeout=3)

    if result.returncode == 0:
        return _parse_jobs(result.stdout)

    return []
